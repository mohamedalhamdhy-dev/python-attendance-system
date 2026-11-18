"""Create .env once. On upgrade, COPY your previous secrets; never rerun this script."""
import base64
import secrets
from pathlib import Path
from urllib.parse import quote

root=Path(__file__).resolve().parents[1]
file=root/'.env'
if file.exists():raise SystemExit('.env already exists. Not overwriting any installation secrets.')
admin_password=secrets.token_urlsafe(20)
mysql_password=secrets.token_urlsafe(24)
backup_key=base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii')
face_key=base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii')
file.write_text(f'''# Private local installation credentials. Never commit this file.
DATABASE_URL=mysql+pymysql://presence_app:{quote(mysql_password,safe='')}@host.docker.internal:3306/presence_saas?charset=utf8mb4
JWT_SECRET={secrets.token_urlsafe(48)}
ADMIN_USERNAME=admin
ADMIN_PASSWORD={admin_password}
APP_TIMEZONE=Asia/Dubai
MIN_CHECKOUT_INTERVAL_MINUTES=30
BIOMETRIC_ENCRYPTION_KEY={face_key}
FACE_MATCH_THRESHOLD=0.47
BACKUP_ENCRYPTION_KEY={backup_key}
BACKUP_DIRECTORY=/app/backups
BACKUP_AT=02:00
BACKUP_TIMEZONE=Asia/Dubai
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULED=true
BACKUP_S3_BUCKET=
BACKUP_S3_PREFIX=presence-attendance
''',encoding='utf-8')
try:file.chmod(0o600)
except OSError:pass
print('Created .env. Keep all credentials private.')
print('Administrator login: admin /',admin_password)
print('XAMPP SQL — run once in phpMyAdmin SQL after changing to the MySQL administrator account:')
print('CREATE DATABASE IF NOT EXISTS presence_saas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
print("CREATE USER IF NOT EXISTS 'presence_app'@'%' IDENTIFIED BY '"+mysql_password+"';")
print("GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES, DROP ON presence_saas.* TO 'presence_app'@'%';")
print('FLUSH PRIVILEGES;')
print('After applying the SQL, protect your .env and terminal output. Remove DDL rights before public deployment.')
