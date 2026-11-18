"""Verify bounded-memory backup encryption with a controlled fake dump executable."""
import base64
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import backup


def test_encrypted_stream_archive(monkeypatch):
    with TemporaryDirectory(prefix='presence-backup-test-') as root:
        executable=Path(root)/'fake-dump'
        executable.write_text('#!/usr/bin/env python3\nimport sys\nsys.stdout.write("CREATE TABLE `example` (`id` int);\\nINSERT INTO `example` VALUES (1);\\n")\n')
        executable.chmod(0o700)
        monkeypatch.setenv('MYSQL_DUMP_EXECUTABLE',str(executable))
        monkeypatch.setenv('DATABASE_URL','mysql+pymysql://presence_app:secret@localhost:3306/presence_saas?charset=utf8mb4')
        monkeypatch.setenv('BACKUP_DIRECTORY',root)
        monkeypatch.setenv('BACKUP_ENCRYPTION_KEY',base64.urlsafe_b64encode(b'Z'*32).decode())
        monkeypatch.delenv('BACKUP_S3_BUCKET',raising=False)
        result=backup.create_backup()
        assert result.is_file() and result.name.startswith('presence-')
        assert backup.verify(result)
        assert b'CREATE TABLE' not in result.read_bytes()
        restored=Path(root)/'recovered.sql.gz'
        backup.decrypt_to_gzip(result,restored)
        import gzip
        assert b'CREATE TABLE' in gzip.decompress(restored.read_bytes())
        import pytest
        with pytest.raises(FileExistsError):backup.decrypt_to_gzip(result,restored)
        assert len(list(Path(root).glob('*.enc')))==1
        data=bytearray(result.read_bytes());data[-1]^=1
        result.write_bytes(data)
        import pytest
        with pytest.raises(Exception):backup.verify(result)
