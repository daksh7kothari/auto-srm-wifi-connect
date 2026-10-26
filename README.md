# SRMIST Wi-Fi auto login

This program keeps the `SRMIST` campus Wi-Fi usable on Windows and Ubuntu. It runs in the background after you sign in, checks internet access every 15 seconds, and signs in at the [SRMIST network portal](https://iac.srmist.edu.in/Connect/PortalMain) after two failed checks. Failed login attempts are spaced at least one minute apart.

It checks whether the internet works rather than reading the Wi-Fi traffic meter. A healthy but idle connection can show **0 Mbps** without needing a new login. The monitor works only while the laptop is awake and your user session is signed in. It continues checking after a normal sleep and wake cycle.

## Files

| File | Purpose |
| --- | --- |
| `.env.example` | Safe template to copy when setting up a new computer |
| `.env` | Your local username and password; ignored by Git |
| `login.py` | Wi-Fi check, internet probe, and browser login |
| `start.ps1` / `start.sh` | Run in a terminal while testing |
| `install-windows.ps1` | Install and start a Windows sign-in task |
| `install-linux.sh` | Install and start an Ubuntu systemd user service |

Keep this project folder in a permanent location after installing. The startup task/service points to its current path.

## 1. Set your credentials

The `.env` file is already present on this computer. On a new computer, copy `.env.example` to `.env` first. Edit `.env` so it contains:

```dotenv
SRM_USERNAME=your-network-username
SRM_PASSWORD=your-network-password
```

Use the credentials you type into the SRMIST network portal. Do not add quotes. Everything after the first `=` is part of the value, so `#` and more `=` characters in a password are fine. Do not post or commit `.env`: it stores the password as plain text. `.gitignore` excludes it, but that does not protect copies you share manually.

## 2. Windows setup and automatic startup

Open PowerShell **in this folder**. Install Python 3 if `python --version` does not work. Then run:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install-windows.ps1
```

The installer checks `.env`, creates a Task Scheduler task named **SRM WiFi Monitor**, and starts it immediately. It also removes the older hourly task from earlier versions. The task runs without a visible window, including on battery power, and starts again whenever you sign in to Windows. Closing the laptop and reopening it does not require another command if your session stays signed in.

Check that it is running:

```powershell
Get-ScheduledTask -TaskName 'SRM WiFi Monitor' | Select-Object TaskName, State
```

`Running` is expected. If it is not running, start it with `Start-ScheduledTask -TaskName 'SRM WiFi Monitor'`. To see login errors directly, stop the task with `Stop-ScheduledTask -TaskName 'SRM WiFi Monitor'`, then run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start.ps1`. Press Ctrl+C when finished and start the task again.

To remove automatic startup:

```powershell
Stop-ScheduledTask -TaskName 'SRM WiFi Monitor'
Unregister-ScheduledTask -TaskName 'SRM WiFi Monitor' -Confirm:$false
```

## 3. Ubuntu setup and automatic startup

Open a terminal **in this folder**. Ubuntu Desktop needs Python 3, NetworkManager, and a working systemd user session:

```bash
sudo apt update
sudo apt install python3-venv network-manager
test -f .env || cp .env.example .env
nano .env
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install --with-deps chromium
bash install-linux.sh
```

The installer restricts `.env` to your user account with `chmod 600`, creates `srm-wifi-monitor.service`, and starts it immediately. It starts again whenever you sign in to Ubuntu. After sleep and wake, the running service resumes its checks.

Check it and read recent output:

```bash
systemctl --user status srm-wifi-monitor.service --no-pager
journalctl --user -u srm-wifi-monitor.service -n 30 --no-pager
```

`active (running)` is expected. To run in a terminal instead, stop the service with `systemctl --user stop srm-wifi-monitor.service`, then run `bash start.sh`. Press Ctrl+C when finished and restart it with `systemctl --user start srm-wifi-monitor.service`.

To remove automatic startup:

```bash
systemctl --user disable --now srm-wifi-monitor.service
rm ~/.config/systemd/user/srm-wifi-monitor.service
systemctl --user daemon-reload
```

## When it signs in

- It checks that the connected Wi-Fi name is `SRMIST`. On other networks, it waits.
- It tests two HTTPS sites. If either works, it leaves the portal alone.
- If both fail on two checks in a row, it opens the portal in a headless browser and submits your credentials.
- It looks for **Network Access Granted** before reporting success. If the portal changes or rejects the login, it reports an error and retries later.

If the internet is down for reasons outside the portal, login may not restore it. For problems, run the foreground command above to see the error. No password is printed by the monitor.
