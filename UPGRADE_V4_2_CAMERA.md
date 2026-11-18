# Presence Attendance SaaS v4.2 — Camera Preview & Face Enrollment Fix

This is an **in-place update to the existing `presence-attendance-saas` project**. It does not create or replace the database, employee accounts, face templates, device pairing, or subscriptions.

## What changed

- **`client/v2.css`**: The camera placeholder now respects its HTML `hidden` attribute. Previously, `.cam-placeholder { display:flex }` kept an opaque placeholder on top of the video even when JavaScript marked it hidden.
- **`client/app.js`**: The kiosk now waits for a playable video stream with real frame dimensions before claiming the camera is ready. It shows specific errors for denied permission, busy webcams, disconnected devices, and non-playing streams. It also lets you choose among discovered cameras, and falls back to the default camera if a saved camera identifier is no longer present.
- **`client/app.js`**: Three clear methods are available: **Face attendance**, **Enroll face biometric**, and **ID + PIN fallback**. Enrollment is one-time and requires the employee's ID, PIN, and consent; after enrollment, face attendance requires no ID/PIN. Enrollment conflict (HTTP 409) explains that the face is already enrolled and directs the user to scan or request an admin reset. Other HTTP 409 responses keep their specific backend error (for example, the minimum check-out interval).
- **`backend/main.py`**: `/api/kiosk/biometric-status` now returns the number of **active enrolled faces in that paired company's tenant**. When none exist, the kiosk prompts enrollment and disables an attempt that would only return 409.
- **`tests/test_workflow.py`**: Regression tests cover the face enrollment count and the already-enrolled conflict.

## Upgrade existing folder

1. Make a copy of your existing project folder. Keep your `.env`, `face_models/`, `backups/`, and XAMPP MySQL database.
2. Extract `Presence_Attendance_SaaS_v4_2_Camera_Hotfix.zip` into your existing `presence-attendance-saas` folder. Its internal `client/`, `backend/` and `tests/` paths are relative to that folder. Overwrite only the matching source files.
3. In a terminal opened in the **existing** project folder, run:

   ```bash
   docker compose up -d --build --no-deps api client
   docker compose ps
   ```

4. Open `http://localhost:8081` and hard-refresh with **Ctrl + Shift + R** to clear old client JavaScript/CSS.
5. Select **Turn on camera**, then approve the camera permission prompt. The camera's image should replace the “Camera is off” overlay. If multiple cameras are connected, choose the right one in the camera dropdown.
6. Select **Enroll face biometric** for the first visit; provide the employee code, PIN, and consent. Three webcam frames are captured to generate an encrypted face template in MySQL. After successful enrollment, use **Face attendance** to scan without credentials.

If the employee is already enrolled, use **Face attendance**. To re-enroll because of a changed appearance or camera issue, the company administrator can choose **Employees → Remove Face** first, then enroll again.

## Troubleshooting

- **Camera permission denied**: In Brave/Chrome, click the camera/site-permissions icon beside `localhost:8081`, allow camera access, then reload. In Windows Settings → Privacy & security → Camera, enable camera access and desktop-app access.
- **Camera busy or black**: Close Windows Camera, Teams, Zoom, OBS or other camera apps. Select the correct USB/integrated webcam. In the terminal, check `docker compose logs --tail=100 client api` for server issues; browser-camera errors appear in the kiosk interface and browser developer tools.
- **Model ready, but not enrolled**: Download and verify the models under `face_models/`, run `docker compose restart api`, then enroll the employee. Model readiness does not mean an employee has already enrolled.
- **409 — Already enrolled**: The current employee already has a template. Scan to check in or remove the old face enrollment using the company administrator's Employees page.
- **409 — Check-out available after 30 minutes**: Attendance was recorded but the application's check-out interval has not yet elapsed. This is an attendance policy conflict, not a camera problem.
- **No enrolled faces**: Register the first employee's face before scanning. Enrollment is **company-scoped**.
- **Camera only available on your PC**: `http://localhost:8081` is a secure context for local development. If you access the kiosk from another device over a LAN/IP address, browsers generally require HTTPS to enable `getUserMedia`.

## Security and hardware limitations

Face identification uses the supplied OpenCV YuNet and SFace models and encrypted templates, but **there is no validated anti-spoofing, liveness, virtual-camera attestation, or production biometric certification**. A face photo or replay may bypass this pilot. Do not deploy it for security-critical attendance without those safeguards.

**Fingerprint reader support is not implemented.** A browser's WebAuthn/Windows Hello interface does not expose reusable fingerprint templates or anonymous 1:N employee identification; real shared-kiosk fingerprint attendance would need a specific supported scanner and its vendor SDK or a trusted device integration. This patch provides two working face-related operations (face enrollment and face attendance), plus the existing PIN fallback.

## Verification notes

- JavaScript syntax and Python compilation validated.
- Backend/API regression suite: **4 tests passed** in an isolated test database (no production/XAMPP data accessed).
- Browser UI mock test checked overlay hiding, enrollment/attendance switching, 409 messages, and JavaScript errors. The video feed was simulated; **real ASUS webcam capture was not testable from this environment**.

The patch has **no schema migration**. Preserve existing `.env` and `BIOMETRIC_ENCRYPTION_KEY`; regenerating the encryption key can make previously enrolled faces unreadable.
