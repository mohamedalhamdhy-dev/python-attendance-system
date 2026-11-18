OpenCV Zoo model files are not bundled in the source ZIP.

Download and SHA-256-verify them by running:

    python scripts/download_face_models.py

Files:
- face_detection_yunet_2023mar.onnx: MIT licensed; OpenCV Zoo YuNet
- face_recognition_sface_2021dec.onnx: Apache-2.0 licensed; OpenCV Zoo SFace

Model distribution and third-party attribution:
https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface

Do not use face-only identification as proof of liveness or protection from a
photo, video replay, deepfake or virtual camera. This is a local-only pilot.
