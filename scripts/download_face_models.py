"""Fetch official OpenCV Zoo face models with pinned SHA-256 verification.

Run from the project root with: python scripts/download_face_models.py
No code or model is fetched at server startup; this operation is explicit.
"""
import hashlib
import os
import shutil
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1] / 'face_models'
BASE = 'https://huggingface.co/opencv/opencv_zoo/resolve/main/models/'
FILES = {
    'face_detection_yunet/face_detection_yunet_2023mar.onnx':
      '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4',
    'face_recognition_sface/face_recognition_sface_2021dec.onnx':
      '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79',
}
MAX_BYTES = 60 * 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run():
    ROOT.mkdir(parents=True, exist_ok=True)
    for remote, expected in FILES.items():
        destination = ROOT / Path(remote).name
        if destination.exists() and digest(destination) == expected:
            print(f'OK (already verified): {destination.name}')
            continue
        tmp = destination.with_suffix('.download')
        print(f'Downloading verified OpenCV model {destination.name} ...', flush=True)
        try:
            with urlopen(Request(BASE + remote, headers={'User-Agent':'PresenceAttendance/2.0'}), timeout=90) as resp, tmp.open('wb') as output:
                copied = 0
                while chunk := resp.read(1024 * 1024):
                    copied += len(chunk)
                    if copied > MAX_BYTES:
                        raise RuntimeError('Unexpectedly large model download')
                    output.write(chunk)
            if digest(tmp) != expected:
                raise RuntimeError(f'SHA-256 mismatch: {destination.name}; download refused')
            os.replace(tmp, destination)
            print(f'Verified: {destination.name} ({copied:,} bytes)')
        except (URLError, OSError, RuntimeError) as exc:
            tmp.unlink(missing_ok=True)
            raise SystemExit(f'Cannot install {destination.name}: {exc}') from None
    print('Both models verified. Ensure .env contains BIOMETRIC_ENCRYPTION_KEY, then docker compose restart api.')

if __name__ == '__main__':
    run()
