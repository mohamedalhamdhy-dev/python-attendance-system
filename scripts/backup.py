"""Encrypted, streamed MySQL backup runner with optional S3 upload.

Usage: python -m scripts.backup --once | --loop | --verify FILE | --decrypt FILE --output PATH
Environment: DATABASE_URL, BACKUP_ENCRYPTION_KEY, BACKUP_DIRECTORY, BACKUP_AT,
BACKUP_TIMEZONE, BACKUP_RETENTION_DAYS, optional BACKUP_S3_BUCKET.
Never writes plaintext SQL to disk; authenticated AES-256-GCM stream.
"""
from __future__ import annotations
import argparse
import base64
import binascii
import hashlib
import logging
import os
import secrets
import subprocess
import sys
import tempfile
import time
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import unquote

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from sqlalchemy.engine import make_url

LOG=logging.getLogger('presence.backup')
MAGIC=b'PABK1'
CHUNK=128*1024


def key():
    try: value=base64.urlsafe_b64decode(os.environ['BACKUP_ENCRYPTION_KEY'].encode('ascii'))
    except (KeyError,ValueError,binascii.Error) as exc:raise RuntimeError('Invalid or missing BACKUP_ENCRYPTION_KEY') from exc
    if len(value)!=32:raise RuntimeError('Backup encryption key must be 32 bytes')
    return value


def db_connection():
    raw=os.environ.get('DATABASE_URL','')
    if not raw.startswith('mysql+pymysql://'):raise RuntimeError('DATABASE_URL must specify a MySQL database')
    url=make_url(raw)
    if not url.database or not url.username:raise RuntimeError('Database connection incomplete')
    return url


def dump_command(url,credential_file):
    command=os.environ.get('MYSQL_DUMP_EXECUTABLE','mysqldump')
    # XAMPP on the Windows host frequently has no TLS server configured.
    # Limit the non-TLS exception to loopback / Docker's Windows host alias.
    tls_mode=os.environ.get('BACKUP_DB_TLS_MODE','auto').lower()
    if tls_mode not in ('auto','required','disabled'):
        raise RuntimeError('BACKUP_DB_TLS_MODE must be auto, required or disabled')
    local_host=(url.host or '').lower() in ('host.docker.internal','localhost','127.0.0.1','::1')
    if tls_mode=='disabled' and not local_host:
        raise RuntimeError('Non-TLS backups are restricted to local XAMPP/MySQL hosts')
    # The installed default-mysql-client is MariaDB on Debian, which supports
    # --skip-ssl. Test this explicitly against your own host installation.
    ssl_args=['--skip-ssl'] if (tls_mode=='disabled' or (tls_mode=='auto' and local_host)) else ['--ssl']
    return [command,'--defaults-extra-file='+str(credential_file),*ssl_args,
            '--single-transaction','--quick','--routines','--triggers','--events',
            '--no-tablespaces','--default-character-set=utf8mb4',url.database]


def create_backup():
    secret=key();url=db_connection()
    output=Path(os.environ.get('BACKUP_DIRECTORY','./backups')).resolve()
    output.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name=f'presence-{stamp}-{secrets.token_hex(4)}.sql.gz.enc'
    final=output/name
    partial=output/(name+'.partial')
    with tempfile.TemporaryDirectory(prefix='presence-credentials-') as private:
        private_dir=Path(private)
        if os.name!='nt':os.chmod(private_dir,0o700)
        config=private_dir/'mysql.cnf'
        # The password is never passed on the command line or emitted to the log.
        # Generated installation secrets use URL-safe characters.
        for item in (url.username,url.password or '',url.host or 'localhost'):
            if any(c in item for c in '\n\r"'):
                raise RuntimeError('Credentials include unsupported config characters')
        config.write_text('[client]\nuser="'+url.username+'"\npassword="'+(url.password or '')+'"\nhost="'+(url.host or 'localhost')+'"\nport='+str(url.port or 3306)+'\n',encoding='utf-8')
        if os.name!='nt':os.chmod(config,0o600)
        process=subprocess.Popen(dump_command(url,config),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            with partial.open('wb') as out:
                if os.name!='nt':os.chmod(partial,0o600)
                nonce=secrets.token_bytes(12)
                encryptor=Cipher(algorithms.AES(secret),modes.GCM(nonce)).encryptor()
                compressor=zlib.compressobj(level=6,wbits=31)  # gzip stream
                out.write(MAGIC+nonce)
                while True:
                    chunk=process.stdout.read(CHUNK)
                    if not chunk:break
                    compressed=compressor.compress(chunk)
                    if compressed:out.write(encryptor.update(compressed))
                out.write(encryptor.update(compressor.flush()))
                out.write(encryptor.finalize())
                out.write(encryptor.tag)
                out.flush();os.fsync(out.fileno())
            stderr=process.stderr.read(8192).decode('utf-8','replace')
            code=process.wait(timeout=60)
            if code!=0:raise RuntimeError('MySQL dump failed: '+stderr[:500])
            partial.replace(final)
        except Exception:
            process.kill();process.wait()
            partial.unlink(missing_ok=True)
            raise
        finally:
            process.stdout.close();process.stderr.close()
    verify(final)
    _retention(output)
    _s3_upload(final)
    LOG.info('Encrypted backup created: %s (%s bytes)',final,final.stat().st_size)
    return final


def verify(path):
    # Streaming MAC verification without storing decrypted data.
    file=Path(path)
    with file.open('rb') as f:
        if f.read(5)!=MAGIC:raise RuntimeError('Incorrect backup format')
        nonce=f.read(12)
        size=file.stat().st_size
        if size<=33:raise RuntimeError('Empty or truncated backup')
        f.seek(-16,2);tag=f.read(16);f.seek(17)
        decryptor=Cipher(algorithms.AES(key()),modes.GCM(nonce,tag)).decryptor()
        remaining=size-17-16
        uncompress=zlib.decompressobj(wbits=31)
        def consume(data):
            # Bound decompressed output: a hostile/invalid gzip stream must not
            # expand unboundedly in the verifier's memory.
            while data:
                uncompress.decompress(data,CHUNK)
                data=uncompress.unconsumed_tail
                if uncompress.eof and data:
                    raise RuntimeError('Unexpected data after gzip end marker')
        while remaining>0:
            data=f.read(min(CHUNK,remaining))
            if not data:raise RuntimeError('Truncated backup payload')
            remaining-=len(data)
            consume(decryptor.update(data))
        consume(decryptor.finalize())
        if not uncompress.eof:raise RuntimeError('Backup gzip stream is incomplete')
    return True


def decrypt_to_gzip(source, target):
    """Verify then recover compressed SQL to a new, permission-restricted file.

    This intentionally does not connect to MySQL or overwrite an existing database.
    The recovered .sql.gz contains sensitive plaintext SQL once decompressed.
    """
    source=Path(source).resolve()
    target=Path(target).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    if target.exists():raise FileExistsError('Refusing to overwrite an existing restore file: '+str(target))
    if target.suffix!='.gz':raise ValueError('Restore destination must end in .gz')
    target.parent.mkdir(parents=True,exist_ok=True)
    verify(source)  # authenticate *before* beginning a restore
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='wb',prefix='.presence-restore-',suffix='.partial',
                                         dir=target.parent,delete=False) as out:
            temporary=Path(out.name)
            if os.name!='nt':os.chmod(temporary,0o600)
            with source.open('rb') as f:
                if f.read(len(MAGIC))!=MAGIC:raise ValueError('Invalid archive')
                nonce=f.read(12)
                f.seek(-16,2);tag=f.read(16);f.seek(len(MAGIC)+12)
                decryptor=Cipher(algorithms.AES(key()),modes.GCM(nonce,tag)).decryptor()
                remaining=source.stat().st_size-len(MAGIC)-12-16
                while remaining>0:
                    chunk=f.read(min(CHUNK,remaining))
                    if not chunk:raise RuntimeError('Unexpected end of encrypted archive')
                    out.write(decryptor.update(chunk))
                    remaining-=len(chunk)
                out.write(decryptor.finalize())
            out.flush();os.fsync(out.fileno())
        # Atomic publish only when no file with the destination name already exists.
        os.link(temporary,target)
    finally:
        if temporary:temporary.unlink(missing_ok=True)
    return target


def _retention(folder):
    keep_days=int(os.environ.get('BACKUP_RETENTION_DAYS','30'))
    if keep_days<=0:return
    cutoff=datetime.now(timezone.utc).timestamp()-keep_days*86400
    for p in folder.glob('presence-*.sql.gz.enc'):
        if p.stat().st_mtime<cutoff:
            p.unlink()


def _s3_upload(file):
    bucket=os.environ.get('BACKUP_S3_BUCKET','').strip()
    if not bucket:return
    import boto3
    prefix=os.environ.get('BACKUP_S3_PREFIX','presence-backups').strip('/')
    s3=boto3.client('s3')
    s3.upload_file(str(file),bucket,f'{prefix}/{file.name}',ExtraArgs={'ServerSideEncryption':'AES256'})
    LOG.info('Encrypted backup uploaded to S3: %s/%s',bucket,file.name)


def loop():
    tz=ZoneInfo(os.environ.get('BACKUP_TIMEZONE','Asia/Dubai'))
    hour,minute=map(int,os.environ.get('BACKUP_AT','02:00').split(':'))
    if not (0<=hour<=23 and 0<=minute<=59):raise RuntimeError('BACKUP_AT must be HH:MM')
    LOG.info('Daily backup service running at %02d:%02d %s',hour,minute,tz)
    while True:
        now=datetime.now(tz)
        target=now.replace(hour=hour,minute=minute,second=0,microsecond=0)
        if now>=target:target+=timedelta(days=1)
        while datetime.now(tz)<target:
            time.sleep(min(60,max(1,(target-datetime.now(tz)).total_seconds())))
        try:
            create_backup()
        except Exception:
            LOG.exception('Scheduled backup failed; check database availability and backup destination')
        time.sleep(60)


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--once',action='store_true')
    mode.add_argument('--loop',action='store_true')
    mode.add_argument('--verify',metavar='FILE')
    mode.add_argument('--decrypt',metavar='FILE')
    parser.add_argument('--output',metavar='FILE')
    args=parser.parse_args()
    if args.decrypt and not args.output:parser.error('--decrypt requires --output')
    if args.output and not args.decrypt:parser.error('--output is only valid with --decrypt')
    if args.loop:loop()
    elif args.verify:print('Verified:',verify(args.verify))
    elif args.decrypt:print('Recovered:',decrypt_to_gzip(args.decrypt,args.output))
    else:print('Created:',create_backup())
