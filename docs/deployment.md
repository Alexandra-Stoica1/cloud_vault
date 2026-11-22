# Deployment on the local network

This guide runs the CloudVault API in production mode (no auto-reload) so that the API, its
Swagger documentation and the admin pages can be opened from any device on the same network.

The web front-end (`cloud_vault_web`) has its own guide in `docs/deployment.md` of that
repository. Start the API first: the web app needs it.

Nothing is installed or changed in Windows besides one firewall question, answered once (step 5).

## Overview

| Program        | Repository        | Port | Address from another device        |
| -------------- | ----------------- | ---- | ---------------------------------- |
| CloudVault API | `cloud_vault`     | 8000 | `http://<computer IP>:8000`        |
| CloudVault Web | `cloud_vault_web` | 3000 | `http://<computer IP>:3000`        |

### Development vs. production

|               | Development                       | Production (this guide)                           |
| ------------- | --------------------------------- | ------------------------------------------------- |
| Command       | `uvicorn app.main:app --reload`   | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Code changes  | reloaded automatically            | restart the command                               |
| Listens on    | `127.0.0.1` (this computer only)  | `0.0.0.0` (every network interface)               |

## 1. Prerequisites

- PostgreSQL is running and the `cloud_vault` database exists.
- The virtual environment and the dependencies are installed (README, steps 2–3).
- `.env` exists with `DATABASE_URL` and `JWT_SECRET_KEY`.

## 2. Find the computer's IP address

```powershell
ipconfig
```

Use the **IPv4 Address of the Wi-Fi adapter** (or Ethernet), e.g. `192.168.1.20`. The rest of
this guide writes it as `<IP>`. Ignore virtual adapters such as `192.168.56.x` (VirtualBox): other
devices cannot reach them.

## 3. Settings and database

In `.env`:

```
DEBUG=true
```

The admin pages keep their session in a cookie that is marked `Secure` (HTTPS only) when
`DEBUG=false`. Over plain `http://` the browser would drop it and the admin login would not work,
so it stays `true` on the local network. The side effect is that unexpected server errors show
their details in the response.

Apply the migrations:

```powershell
.venv\Scripts\alembic.exe upgrade head
```

## 4. Start

From the `cloud_vault` folder:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- No `--reload`: the code is loaded once, as in production.
- `--host 0.0.0.0` listens on every network interface, so other devices can connect. Without it,
  uvicorn only accepts connections from this computer.
- Keep the terminal open: closing it stops the API.

## 5. Allow the connection in Windows Firewall

The first time the API listens on the network, Windows asks whether **Python** may accept
connections. Choose **Allow**. If the Wi-Fi is marked as a **Public** network, tick the public
networks option in that dialog; otherwise other devices are blocked.

This only lets `python.exe` receive connections; no protection is turned off.

## 6. Open it from another device

The device must be on the **same network** (same Wi-Fi). Replace `<IP>` with the address from
step 2:

| Address                    | What it shows                  |
| -------------------------- | ------------------------------ |
| `http://<IP>:8000/health`  | `{"status": "ok", ...}`        |
| `http://<IP>:8000/docs`    | Swagger UI with every endpoint |
| `http://<IP>:8000/login`   | login for the admin pages      |

## 7. Start the web app

Follow `docs/deployment.md` in `cloud_vault_web`. The web app runs on the same computer and calls
the API on `http://127.0.0.1:8000`.

## Security on a shared network

- The migrations create demo accounts with a known password, including the administrator
  `admin@example.com`. Anyone on the same network can sign in with them. Use a trusted network
  (e.g. your home Wi-Fi), or change the administrator's password before starting.
- Everything runs over plain HTTP, so traffic is not encrypted. That is acceptable for a local
  demo, not for real data.
- Stop both commands (Ctrl+C) when you no longer need them.

## Troubleshooting

| Problem                                            | Cause and fix                                                                            |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Works on this computer but not on another device   | Missing `--host 0.0.0.0`, wrong IP (step 2), other Wi-Fi, or the firewall question was refused (step 5). |
| `/health` returns an error                         | PostgreSQL is not running or `DATABASE_URL` is wrong.                                   |
| Admin login returns to the login page              | `DEBUG=false` in `.env` (step 3); set it to `true` and restart.                          |
| `address already in use` on port 8000              | Another uvicorn is running (e.g. with `--reload`); stop it first.                        |
