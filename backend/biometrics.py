"""Real OpenCV YuNet + SFace embeddings; NOT presentation-attack/liveness detection.

Images are decoded in memory, never persisted. Encrypted templates live in MySQL.
The matching threshold is conservative for a *pilot*, not a calibrated production FAR.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import os
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MODEL_DIR = Path(os.getenv('FACE_MODEL_DIR', '/app/face_models'))
DETECTOR_PATH = MODEL_DIR / 'face_detection_yunet_2023mar.onnx'
RECOGNIZER_PATH = MODEL_DIR / 'face_recognition_sface_2021dec.onnx'
MODEL_VERSION = 'opencv-yunet-2023mar+sface-2021dec'
MODEL_HASHES = {
    DETECTOR_PATH.name: '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4',
    RECOGNIZER_PATH.name: '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79',
}
MATCH_THRESHOLD = float(os.getenv('FACE_MATCH_THRESHOLD', '0.47'))
AMBIGUITY_MARGIN = 0.08
_INFERENCE_LOCK = Lock()
_DETECTOR = None
_RECOGNIZER = None

class FaceUnavailable(RuntimeError):
    pass

class FaceRejected(ValueError):
    pass


def _key() -> bytes:
    value = os.getenv('BIOMETRIC_ENCRYPTION_KEY', '')
    try:
        key = base64.urlsafe_b64decode(value.encode('ascii'))
    except (ValueError, binascii.Error, UnicodeError):
        raise FaceUnavailable('Invalid biometric encryption key') from None
    if len(key) != 32:
        raise FaceUnavailable('BIOMETRIC_ENCRYPTION_KEY must be a 32-byte base64 key')
    return key


def available() -> bool:
    try:
        _key()
    except FaceUnavailable:
        return False
    return all(p.is_file() and p.stat().st_size > 100_000 for p in (DETECTOR_PATH, RECOGNIZER_PATH))


def encrypt_vector(vector: np.ndarray, employee_id: int) -> str:
    nonce = os.urandom(12)
    aad = f'presence:face:v1:{employee_id}'.encode()
    payload = vector.astype(np.float32).tobytes()
    return base64.b64encode(nonce + AESGCM(_key()).encrypt(nonce, payload, aad)).decode('ascii')


def decrypt_vector(blob: str, employee_id: int) -> np.ndarray:
    data = base64.b64decode(blob, validate=True)
    if len(data) < 29:
        raise FaceUnavailable('Face template is invalid')
    raw = AESGCM(_key()).decrypt(data[:12], data[12:], f'presence:face:v1:{employee_id}'.encode())
    vec = np.frombuffer(raw, dtype=np.float32).copy()
    if vec.size != 128:
        raise FaceUnavailable('Face template has an unexpected size')
    return _normalized(vec)


def _normalized(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if not np.isfinite(norm) or norm < 1e-8:
        raise FaceRejected('Unable to extract reliable face features')
    return np.asarray(vec / norm, dtype=np.float32).reshape(-1)


def _models():
    global _DETECTOR, _RECOGNIZER
    if not available():
        raise FaceUnavailable('Biometrics disabled: configure the encryption key and install both OpenCV models')
    if _DETECTOR is None or _RECOGNIZER is None:
        for path in (DETECTOR_PATH, RECOGNIZER_PATH):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != MODEL_HASHES[path.name]:
                raise FaceUnavailable('Face model integrity check failed; reinstall verified models')
        try:
            _DETECTOR = cv2.FaceDetectorYN.create(str(DETECTOR_PATH), '', (320, 320), 0.92, 0.3, 5000)
            _RECOGNIZER = cv2.FaceRecognizerSF.create(str(RECOGNIZER_PATH), '')
        except cv2.error as exc:
            _DETECTOR = None
            _RECOGNIZER = None
            raise FaceUnavailable('OpenCV face models could not be loaded') from exc
    return _DETECTOR, _RECOGNIZER


def extract(image_base64: str) -> np.ndarray:
    """Validate frame dimensions/content, require exactly one detectable face, return SFace embedding."""
    if not isinstance(image_base64, str) or len(image_base64) > 1_100_000:
        raise FaceRejected('Camera frame too large or missing')
    try:
        raw = base64.b64decode(image_base64, validate=True)
    except (ValueError, binascii.Error):
        raise FaceRejected('Invalid camera image encoding') from None
    if not raw.startswith(b'\xff\xd8\xff') or len(raw) > 800_000:
        raise FaceRejected('Only JPEG images up to 800 KB are accepted')
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FaceRejected('Invalid camera image')
    height, width = image.shape[:2]
    if width < 320 or height < 240 or width > 1280 or height > 1280:
        raise FaceRejected('Camera resolution must be between 320x240 and 1280x1280')
    # A single global lock protects OpenCV's stateful model objects in threaded FastAPI requests.
    with _INFERENCE_LOCK:
        detector, recognizer = _models()
        try:
            detector.setInputSize((width, height))
            _, faces = detector.detect(image)
            if faces is None or len(faces) != 1:
                raise FaceRejected('Position exactly one face in front of the camera')
            face = faces[0]
            if min(face[2], face[3]) < 95:
                raise FaceRejected('Move closer to the camera and ensure even lighting')
            aligned = recognizer.alignCrop(image, face)
            return _normalized(recognizer.feature(aligned))
        except cv2.error as exc:
            raise FaceRejected('Unable to process this face frame') from exc


def enroll(images: list[str]) -> np.ndarray:
    if len(images) != 3:
        raise FaceRejected('Enrollment requires exactly three camera captures')
    embeddings = [extract(frame) for frame in images]
    # Require consistent identity over all three samples; no automated liveness claim.
    for i in range(3):
        for j in range(i + 1, 3):
            if similarity(embeddings[i], embeddings[j]) < MATCH_THRESHOLD:
                raise FaceRejected('Faces differ between captures. Repeat enrollment in good lighting.')
    return _normalized(np.mean(embeddings, axis=0))


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def identify(frame: str, templates: list[tuple[int, str]]) -> int | None:
    query = extract(frame)
    scores = sorted(((similarity(query, decrypt_vector(blob, eid)), eid) for eid, blob in templates), reverse=True)
    if not scores or scores[0][0] < MATCH_THRESHOLD:
        return None
    if len(scores) > 1 and scores[0][0] - scores[1][0] < AMBIGUITY_MARGIN:
        return None
    return scores[0][1]
