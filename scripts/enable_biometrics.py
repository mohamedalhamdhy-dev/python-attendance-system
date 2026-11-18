"""Safely add a permanent biometric encryption key to an existing installation.

Never overwrite existing .env keys; biometric embeddings become unreadable if key is lost.
"""
import base64
import os
from pathlib import Path

path = Path(__file__).resolve().parents[1] / '.env'
if not path.exists():
    raise SystemExit('Missing .env; run python scripts/setup_env.py once for a new installation.')
content = path.read_text(encoding='utf-8')
if any(line.strip().startswith('BIOMETRIC_ENCRYPTION_KEY=') for line in content.splitlines()):
    raise SystemExit('BIOMETRIC_ENCRYPTION_KEY already present. Kept existing key unchanged.')
key = base64.urlsafe_b64encode(os.urandom(32)).decode('ascii')
with path.open('a', encoding='utf-8') as out:
    if content and not content.endswith('\n'):
        out.write('\n')
    out.write('# Keep this key securely backed up; losing it makes face templates unrecoverable.\n')
    out.write('BIOMETRIC_ENCRYPTION_KEY=' + key + '\n')
try:
    path.chmod(0o600)
except OSError:
    pass
print('Enabled encrypted biometric templates in the existing .env (previous secrets preserved).')
print('Back up .env securely. Never commit or share it.')
