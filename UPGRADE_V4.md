# Presence Attendance v4 — in-place upgrade of your existing v3 project

**This is an update to the same `presence-attendance-saas` project and the same XAMPP `presence_saas` database.** The ZIP does not contain `.env`, passwords, face model ONNX files, or your `backups/` archives. Do not regenerate `.env` and do not create a new database. The first API launch will add the employee portal password columns without deleting employee or attendance records.

## Before you change anything

1. In XAMPP, leave your MySQL/MariaDB server running. Use **phpMyAdmin → presence_saas → Export → Quick or Custom → SQL** to export a snapshot to a protected local location. Check that the downloaded file is not empty. Keep an offline protected copy. An export is not the same as a verified restore; if this deployment is important, also test importing into a separate temporary database.
2. Make a backup copy of the **entire existing** `presence-attendance-saas` folder, including `.env`, `face_models/` and `backups/`, in a location accessible only to you. These are sensitive; do not upload them to public storage or send them to chat.
3. In **your existing** `presence-attendance-saas` folder, run:

   ```bash
   docker compose down
   ```

   **Never use `docker compose down -v` for an upgrade.** This project uses XAMPP MySQL, so `down` does not erase that database.

4. Extract **either** the complete-source ZIP **or** the patch ZIP into **the existing `presence-attendance-saas` folder**, allowing matching source files to be replaced. If extracting the complete ZIP, open its top-level `presence-attendance-saas/` directory first so you don't accidentally create `presence-attendance-saas/presence-attendance-saas/`. Do not overwrite or delete `.env`, `face_models/` or `backups/`.

## Start and verify

Open Git Bash or Command Prompt **in that existing folder**:

```bash
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 api
```

The `api`, `admin`, `company`, `client`, and `backup-runner` containers should be running. The website containers and API include healthchecks. The API initializes/migrates the existing MySQL schema. Your database user requires `ALTER` permissions for the new employee account fields during this migration.

| Entry point | Local website | Sign in with |
|---|---|---|
| **SuperAdmin** | http://localhost:8080 | Existing platform admin account |
| **Company Portal** | http://localhost:8082 | Existing company admin account (same credentials as v3) |
| **Attendance Kiosk** | http://localhost:8081 | Paired kiosk (no admin login) |
| **Employee Attendance History** | http://localhost:8081/employee.html | Company URL slug + employee code + a separate portal password, set by an administrator |
| **Status page** | `http://localhost:8080/status.html`, or the same `/status.html` path on ports 8082 and 8081 | No sign-in; limited, non-sensitive checks |

### First test

1. Visit `http://localhost:8080` using the platform administrator login. Click **Companies**. You can **Register Company**, grant subscriptions, or **Reset admin password** for a company administrator.
2. Visit `http://localhost:8082` using a previously registered company's admin login. Click **Employees → Reset portal password** beside an existing employee. Set a **new, unique password (12+ characters)**. This does not reset their kiosk PIN or biometric face enrollment.
3. Open `http://localhost:8081/employee.html` and enter the **company slug** (for example `kings-palace`, not the display name), employee code, and portal password. You should see **only that employee's own attendance calendar**. Change password from that page if desired.
4. Verify each site's **System Status** page and the status link under the management portal navigation. These checks monitor the three website frontends, API, MySQL and recent kiosk heartbeats; they are not an external uptime SLA.
5. Try **Theme Studio**. Both management portals offer 12 color themes. SuperAdmin's theme choice is saved in that browser's local storage; the Company Portal theme settings are stored in MySQL and applied to the company's paired kiosk.

### Backups with local XAMPP

This release fixes the earlier `SSL is required, but the server does not support it` dump failure for **local** XAMPP connections: the backup utility automatically skips SSL only for `host.docker.internal`, `localhost` and other loopback hosts. Remote backup connections still take the TLS-enabled path. You can explicitly set `BACKUP_DB_TLS_MODE=auto` in `.env` (optional — `auto` is the default). Do not disable TLS for a remote database. For production, configure TLS trust/certificate verification and test restores.

Test a manual encrypted backup:

```bash
docker compose exec backup-runner python -m scripts.backup --once
docker compose logs --tail=100 backup-runner
```

A file ending in `.sql.gz.enc` should appear in the existing `backups/` directory. The **daily schedule still requires your PC, XAMPP and Docker to stay running**.

### Troubleshooting

- Company login returning *not found*: make sure you are visiting **port 8082**, not 8080, and the `company` container is present in `docker compose ps`. Try `docker compose logs --tail=100 company`.
- Old v3 Company Admin token on 8080: sign out of port 8080; company accounts now sign in at 8082, in a separate browser origin.
- API unhealthy: `docker compose logs --tail=150 api` and check that XAMPP MySQL is started and port 3306 in `.env` matches its configuration. Never paste `.env` or passwords into chat.
- Existing employees cannot sign in to the new employee history page until an administrator has set their **portal password**. The old kiosk PIN is not a portal password.
- If the app reports `ALTER TABLE` permission denied on startup, the `presence_app` database user needs temporary schema migration privileges; do not recreate or empty the database.
- For camera/biometrics, the existing ONNX files must remain in `face_models/` and `BIOMETRIC_ENCRYPTION_KEY` must be preserved. Face matching remains **pilot-only** until anti-spoof/liveness controls are validated.

## Security & scope

Password resets are administrator-authorized, tenant-scoped and invalidate existing JWT sessions. The new employee password is hashed with Argon2id, and the original PIN/face recognition pipeline is unchanged. Keep initial passwords out of email and publicly shared messages; give them to employees via a controlled channel and have them change the password. This upgrade **does not add** MFA, verified anti-spoofing, payment gateway processing, audited SaaS production security or automatic internet hosting. Do not expose this local XAMPP deployment publicly without hardening.
