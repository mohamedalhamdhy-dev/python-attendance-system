# Presence Attendance — Multi-Company Admin + Kiosk (SaaS Pilot v4)

This repository contains an installable **local multi-tenant attendance SaaS pilot**, consisting of a platform SuperAdmin web dashboard, self-registered company portals, independently paired company kiosks, a shared FastAPI API, and a **single XAMPP-hosted MySQL/MariaDB** database. It builds on the previous Presence Attendance source but is **not a certified biometric security product or a payment-processing service**.

**Already running v3?** Follow [UPGRADE_V4.md](UPGRADE_V4.md) to update the **same existing project directory** and **same XAMPP database**. Keep `.env`, `face_models/`, and `backups/` unchanged.

## What is implemented

| Area | Current functionality |
| --- | --- |
| Platform SuperAdmin | Dedicated website on **8080**; register companies, reset company admin or employee portal passwords, grant subscriptions, global attendance, system status and backups |
| Company portal | Dedicated website on **8082**; self-registration, employee and PIN management, employee password resets, kiosk pairing, attendance, calendar and themes |
| Multi-tenancy | All company employee, kiosk, face-template and attendance queries are restricted to the authenticated tenant; platform administrator is a separate role |
| Attendance website | Dedicated **8081** kiosk; one-time pairing, switch/unpair building, face-enrollment workflow and optional PIN fallback. Employee self-service calendar at `/employee.html` |
| Biometrics | Optional **real OpenCV YuNet + SFace** local-model facial recognition; encrypted face embeddings in MySQL and consent at enrollment. Requires separately downloaded model files. NOT spoof-resistant/liveness-certified. |
| Attendance calendar | Employee-specific month grid, colored daily states, check-in and check-out clock times |
| Live dashboard | Automatic data refresh every ~4 seconds; notification badges on related navigation items and browser tab, optional sounds and desktop notifications (browser must remain open) |
| Subscription demo | Registration: 7-day free trial OR monthly **AED 100 / 30 days** OR annual **AED 1,000 / 365 days**. Expired trials cannot continue check-ins. Checkout creates a **pending local order**, not a real charge. SuperAdmin can approve/grant. |
| Theme studio | 12 preset light/dark color themes for both management portals; Company kiosk inherits its company theme. Company customization supports accent, font and layout density. |
| Backup | Daily encrypted, authenticated MySQL dumps saved in `backups/` on the computer hosting Docker, optional S3 upload using your own S3 bucket and credentials; manual backup, verification and decrypt-for-restore tools |
| Deployment | Docker for the API and the two Nginx web UIs; local XAMPP MySQL instead of a Docker-managed MySQL container |

### Important biometric/security limitations

**Face matching is real only when both verified OpenCV models are installed and compatible**. It is **not proof that a live person is present**: a printed photo, screen replay, virtual camera or deepfake can still fool this baseline. The system does **not** currently have a validated presentation attack detector (PAD), hardware attestation, WebAuthn/TOTP 2FA, mTLS device certificates, tamper-evident audit chain, or penetration-tested public SaaS security. Face-only check-in is a **local pilot workflow**, not appropriate for security-critical/payroll decisions or public commercial deployment until those controls and biometric/privacy governance are implemented and tested. No actual credit cards or payments are collected. Never market checkout as payment collection or completion.

## Requirements (Windows 10/11)

- **Docker Desktop**, using Linux containers and WSL2, must be running.
- **XAMPP** with **MySQL/MariaDB** started in the XAMPP Control Panel. Docker must be able to reach the Windows database using `host.docker.internal` on port 3306. Newer XAMPP installations often use MariaDB, which may not be fully interchangeable with older MySQL dumps.
- **Python 3.10+** installed on Windows to generate installation secrets (and optionally download face models).
- A current Chrome or Edge browser. For camera access, use `localhost` or correctly configured HTTPS.
- Do not put the source project inside an automatically synchronized cloud folder when possible (e.g., move it from OneDrive to `C:\Projects\presence-attendance-saas`); file locks and synced `.env`/backup secrets can be a problem.

## Install from scratch with XAMPP (Windows)

1. **Make a copy of your previous installation and database before making changes.** Extract this ZIP into a **new folder**, for example `C:\Projects\presence-attendance-saas`; do not merge it over the old folder. Stop the previous app so ports 8080/8081 are free by running `docker compose down` **inside the OLD project folder**. **Never run `docker compose down -v` on the old project.** The old Docker MySQL volume remains intact with `down` (no `-v`).

2. In the XAMPP Control Panel, click **Start** beside MySQL. Open phpMyAdmin as the local MySQL administrator (usually `http://localhost/phpmyadmin`) and go to its **SQL** tab.

3. Open PowerShell or Git Bash **inside the new extracted folder** and generate private credentials **once**:

   ```powershell
   py scripts\setup_env.py
   ```

   If using Git Bash rather than PowerShell: `python scripts/setup_env.py`. This prints your **initial SuperAdmin password** and the SQL statements for creating the database and dedicated user. **Copy the printed SQL into phpMyAdmin's SQL tab and execute it**. Do not paste or share the resulting password or `.env` with anyone. The `.env` is excluded from ZIP and version control.

4. Ensure XAMPP MySQL listens on TCP port **3306**. The application's `.env` defaults to:

   ```ini
   DATABASE_URL=mysql+pymysql://presence_app:<generated-password>@host.docker.internal:3306/presence_saas?charset=utf8mb4
   ```

   The setup script writes the real generated password. **Do not use the placeholder shown above**. If XAMPP uses another port, edit only the port in `DATABASE_URL` accordingly. The database must be reachable from Docker Desktop; on Windows some configurations require a local firewall rule or a MySQL bind-address setting. Limit access to the local computer/Docker and never open MySQL directly to the Internet. The printed setup SQL uses `'presence_app'@'%'` so the Docker container can authenticate; that host wildcard must be paired with an appropriately restricted firewall/network configuration. The initial user has schema modification privileges to create tables; remove these privileges when a managed migration process is in place.

5. Build and start:

   ```powershell
   docker compose up --build -d
   docker compose ps
   ```

   You should see **api** healthy, **admin**, **company**, **client** and **backup-runner** running. If the API fails, run `docker compose logs --tail=120 api`; for backup failures, `docker compose logs --tail=120 backup-runner`.

6. Visit:

   - **Platform SuperAdmin:** http://localhost:8080
   - **Company Portal:** http://localhost:8082
   - **Employee self-service:** http://localhost:8081/employee.html
   - **Client Kiosk:** http://localhost:8081

7. Sign in to the platform with username **`admin`** and the generated password printed in step 3. Change the password immediately under Settings. On the **Company Portal** login screen (port 8082), other businesses can use **Register company**. SuperAdmin can also register companies from **Companies → Register Company**.

> A fresh install starts with an empty `presence_saas` database. Installing v4 fresh against XAMPP **does not copy** existing employee/attendance records from the old Docker MySQL volume. See the migration section below if you need them.

## Register a company, choose a plan, and check in

1. Open **Company Portal** at `http://localhost:8082` and select **Register company**. Create a company such as **Kings Palace Real Estate**, its own company administrator, and a **7-day trial**. Monthly and annual selections instead create a pending order for manual approval (no funds are collected).
2. Log in with the company's admin credentials. This company portal manages **only its own** employees, kiosks, reports, theme and billing. The platform SuperAdmin has a separate **Companies** view.
3. Company → **Employees → Add Employee**. Use an employee ID, private PIN, name, and department.
4. Company → **Kiosk Fleet → Register Kiosk**, e.g., `Main Entrance` / `Building A`. Copy the **single-use pairing code** displayed by the admin.
5. Open the Kiosk at http://localhost:8081, enter that code and pair. Use **Switch building / Unpair** to invalidate the existing kiosk credential and enter a different building's pairing code. Only the company admin can create new pairing codes.
6. For **PIN attendance**, choose PIN check-in/check-out. For **one-time facial enrollment**, install the optional OpenCV models first (next section), choose **Enroll Face**, enter employee ID/PIN **once**, explicitly consent, and capture three images using a camera. After enrollment, subsequent check-ins/check-outs can use **Face Check-In** without employee ID/PIN. The system chooses check-out after an open check-in; the interval is controlled by `MIN_CHECKOUT_INTERVAL_MINUTES` (default 30 minutes).
7. Company → **Employees** → an employee's **Attendance Calendar** shows the month grid with the check-in/check-out times and status. The dashboard and notifications refresh without manually refreshing the tab (approximately every 4 seconds).
8. Company → **Subscription** displays trial status and plan choices. The checkout/cart review leads to a **pending demo order**. SuperAdmin → **Subscription Orders** can manually approve it. SuperAdmin can also grant company plans directly. The subscription status is enforced by the API; its expiry is based on UTC timestamps, not just a browser display.

## Enable optional face recognition (pilot mode)

Two official OpenCV Zoo models are **not bundled** in the ZIP (they are downloaded explicitly and checksum-verified): YuNet face detector and SFace recognizer. In the project folder:

```powershell
py scripts\download_face_models.py
```

Then restart the API:

```powershell
docker compose restart api
```

The fresh-install `.env` already includes a securely generated `BIOMETRIC_ENCRYPTION_KEY`. Only if upgrading a much older `.env` **without** that key, run `py scripts\enable_biometrics.py` once (it refuses to replace an existing key). If the script requests a rebuild, run `docker compose up --build -d`. Check `docker compose logs --tail=80 api` if a model fails to load. **A webcam, browser permission, sufficiently good lighting and exactly one face** are required. This code has NOT been tested end-to-end against your physical webcam/hardware; the test suite uses controlled embedding vectors and verifies API/storage/role behavior only.

**Privacy:** encrypted embeddings are stored in MySQL. Raw camera images are decoded in memory and not deliberately retained. Obtaining and withdrawing lawful employee consent, limiting access, documenting retention, appropriate notices, data deletion and independent biometric/security testing remain your responsibilities before real use.

## Attendance updates, alerts and browser sound

When a kiosk records a check-in or check-out, the API commits a notification event and the company dashboard polls for updates at about **four-second intervals**. The affected navigation item's badge and the page's top notification count update; optional desktop notification and sound can be enabled in **Admin → Settings**. Browser sound/notifications may require a user interaction and explicit browser permission. Notifications **do not** run as a native system service and will not arrive when the admin browser is closed. This is polling, not a persistent WebSocket connection.

## Scheduled encrypted backups (local + optional S3 cloud)

The `backup-runner` container runs automatically **at 02:00 Asia/Dubai each day**, as long as Docker Desktop, XAMPP MySQL and the computer are running. It creates a MySQL logical dump compressed to gzip and **stream-encrypted with AES-256-GCM**, saved as `backups/presence-YYYYMMDDTHHMMSSZ-XXXXXXXX.sql.gz.enc` in your **new project folder on the local PC**. By default it retains 30 days of backup files. The SuperAdmin **Backup Center** lists and allows downloading these encrypted archives. These are logical database dumps, not OS/VSS snapshots.

Run an immediate backup to test the connection and permissions:

```powershell
docker compose exec backup-runner python -m scripts.backup --once
docker compose logs --tail=70 backup-runner
```

Verify an archive without restoring it (replace `ACTUAL-FILE.sql.gz.enc` with the filename shown in your local `backups` folder):

```powershell
docker compose exec backup-runner python -m scripts.backup --verify /app/backups/ACTUAL-FILE.sql.gz.enc
```

To **decrypt an authenticated backup into a compressed SQL dump** for a *controlled manual recovery*, with a new output filename that does not already exist:

```powershell
docker compose exec backup-runner python -m scripts.backup --decrypt /app/backups/ACTUAL-FILE.sql.gz.enc --output /app/backups/restore-for-import.sql.gz
```

This writes `backups/restore-for-import.sql.gz` on the Windows host. It is **no longer encrypted** and contains private data. Create a *separate test database* in XAMPP and import it using phpMyAdmin's **Import** feature (if your version supports gzipped SQL). Test the restore and delete the unencrypted `.sql.gz` securely; never restore directly over a production database without an approved recovery plan. Existing schema/data and database version compatibility must be evaluated before importing. If the restore cannot be imported by phpMyAdmin, use a compatible MySQL/MariaDB CLI to decompress and import into an explicitly selected test database.

**Backups are unusable if you lose the `BACKUP_ENCRYPTION_KEY` in your `.env`!** Keep an offline, securely stored copy of the backup key. If you lose the biometric key, saved facial templates cannot be decrypted. Do not copy `.env` to a public folder or Git repository. A daily automated backup is **not** guaranteed if your machine is powered off at 02:00; use a continuously running machine/server for reliable scheduling.

For optional cloud S3 upload, set `BACKUP_S3_BUCKET` and `BACKUP_S3_PREFIX` in `.env`, configure AWS credentials via a restricted IAM identity/role for that bucket, and recreate the backup runner:

```powershell
docker compose up -d --force-recreate backup-runner
```

**S3 is optional and is not connected by default.** The code uses `boto3` and attempts to upload the **already encrypted** archive. Network access, AWS credentials, bucket permissions, retention rules and any cloud charges are your responsibility. If cloud upload fails, the local backup is kept and the runner logs the error. XAMPP data remains on your Windows installation, not in a Docker database volume.

## Upgrade existing Presence Attendance data safely

**Do not erase the original MySQL volume.** The previous project uses a Docker-managed **MySQL 8.4 database named `presence`**, whereas this version connects to a distinct local XAMPP database named **`presence_saas`**.

If you need your old data:

1. Preserve the old project folder, old `.env`, encryption keys and Docker volume; make a verified backup first. To export data, while running Docker Compose **in your OLD project folder**, use a shell with redirection (for example Git Bash):

   ```bash
   docker compose exec -T db sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers presence' > presence-legacy.sql
   ```

2. **Stop the old project with `docker compose down` (no `-v`)** so the 8080/8081 ports become available. Start XAMPP MySQL and make a new database plus a verified backup of it before importing.
3. **Do not blindly import a MySQL 8.4 dump into XAMPP MariaDB.** Verify dump and server compatibility first. MySQL 8 collations, generated columns or other syntax may require conversion using a compatible MySQL server/import tool; unvalidated text replacements can corrupt data. Import the dump into `presence_saas` only after that compatibility check, before starting the new API.
4. The API's `backend/upgrade.py` contains a **forward-only, idempotent legacy bridging procedure** that maps existing employees and kiosks into a tenant named **Legacy Workspace**. It runs during API startup and can modify schema; take a restore-tested copy of the database before the first startup. Existing employee IDs/attendance are intended to remain intact; there is no automatic claim of zero-downtime migration.
5. You may then transfer that tenant's employees and kiosks into a *newly registered empty company* after inspecting a dry run:

   ```powershell
   docker compose exec api python -m scripts.transfer_legacy --company kings-palace
   docker compose exec api python -m scripts.transfer_legacy --company kings-palace --apply
   ```

   Replace `kings-palace` with your registered company's exact slug. The destination must be empty. Back up before `--apply`. The original platform administrator may retain its old password if imported from the previous database; the new `.env` bootstrap credential only creates an administrator when one does not exist.

**Prefer a fresh database for initial testing** and migrate historical records only once you've tested a full round trip of the export, import, schema conversion and data verification.

## Developer tests

```powershell
py -m pip install -r backend\requirements.txt pytest httpx
py -m pytest -q tests
```

The automated API tests deliberately use isolated temporary SQLite **only as a test substitute**. **Runtime source of truth is XAMPP MySQL/MariaDB**, and the API refuses non-MySQL database connections outside tests. Tests check tenancy isolation, pairing, PIN attendance, subscription expiry/approval, mock biometric embeddings, notifications and backup encryption/decryption/tamper detection. JavaScript syntax checks: `node --check admin/app.js` and `node --check client/app.js`.

**Verification limits:** The project has not yet undergone a full Docker+XAMPP smoke test on your Windows hardware, external MySQL schema migration test, webcam face-model end-to-end test, security audit, load test, accessibility audit or payment-provider validation. Do not expose it to the public Internet or sell it as production-ready SaaS until those are completed.

## Source layout

```text
presence-attendance-saas/
├── admin/              # Platform + company Admin Dashboard (HTML, JS, CSS)
├── client/             # Full-viewport kiosk, enrollment, pairing, Arabic/English
├── backend/            # FastAPI endpoints, tenant-scoped data, auth, OpenCV face templates
├── ui/shared/          # 12 theme CSS token sets
├── scripts/            # .env setup, verified model downloader, backup, legacy transfer
├── face_models/        # Optional downloaded OpenCV ONNX models (not bundled)
├── backups/            # Local encrypted archives (not bundled)
├── tests/              # Isolated API and crypto workflow tests
├── docker-compose.yml # Nginx platform/company/client + API + backup runner (XAMPP MySQL)
├── .env.example
└── README.md
```

## Planned work before public hosting

A production SaaS requires formal versioned migrations (Alembic), hardened tenant onboarding and password reset, administrator MFA/passkeys, rate limits on all public endpoints, tenant-aware authorization reviews, more reliable device identity/mTLS and kiosk attestation, signed configurations, validated active liveness/PAD (ISO 30107 test methodology and hardware-specific validation), consent/data subject workflows and retention, real invoicing/payment gateway and webhook reconciliation, email delivery, tested recovery and background job infrastructure, TLS/reverse-proxy hosting, structured metrics/alerts, a privacy/security review, and full legal review of biometric attendance in all target regions. Local XAMPP is appropriate for pilot development, not public SaaS hosting.

## New in v4

- Separate locally hosted UI origins (`8080` SuperAdmin, `8082` Company, `8081` Kiosk) with role-specific login views.
- SuperAdmin company-admin password reset and all-tenant employee portal-password reset; company admins can reset employee portal passwords for their own employees.
- Employee-only attendance calendar login on the kiosk website at `/employee.html`, with company slug, employee code and distinct portal password (not PIN).
- Portals/system/API health status pages and 12 retained customizable light/dark themes.
- XAMPP-local backup client TLS compatibility update.

Refer to [UPGRADE_V4.md](UPGRADE_V4.md) for the exact in-place update procedure.
