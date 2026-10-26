"""Monitor SRMIST Wi-Fi and sign in when internet access stops working."""

import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
PORTAL = "https://iac.srmist.edu.in/Connect/PortalMain"
PROBES = ("https://www.cloudflare.com/cdn-cgi/trace", "https://example.com/")
CHECK_INTERVAL = 15
RETRY_INTERVAL = 60


def credentials():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip() in ("SRM_USERNAME", "SRM_PASSWORD"):
            values[key.strip()] = value
    if not values.get("SRM_USERNAME") or not values.get("SRM_PASSWORD"):
        raise ValueError("Set SRM_USERNAME and SRM_PASSWORD in .env before starting.")
    return values["SRM_USERNAME"], values["SRM_PASSWORD"]


def is_srmist_wifi(output, system):
    if system == "nt":
        return bool(re.search(r"(?im)^\s*SSID\s*:\s*srmist\s*$", output))
    return any(line.strip().lower() in ("yes:srmist", "*:srmist", "srmist") for line in output.splitlines())


def wifi_connected():
    commands = (["netsh", "wlan", "show", "interfaces"],) if os.name == "nt" else (
        ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
        ["iwgetid", "-r"],
    )
    for command in commands:
        try:
            output = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=10, check=True)
            return is_srmist_wifi(output.stdout, os.name)
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return False


def internet_works():
    for url in PROBES:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200 and urlparse(response.url).hostname == urlparse(url).hostname and response.read(64):
                    return True
        except (OSError, ValueError):
            continue
    return False


def browser_path():
    candidates = (
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
    )
    for path in candidates:
        if path.is_file():
            return str(path)
    return shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")


def login(username, password):
    with sync_playwright() as playwright:
        path = browser_path()
        browser = playwright.chromium.launch(executable_path=path, headless=True) if path else playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(PORTAL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_function(
                "document.querySelector('#LoginUserPassword_auth_username') || "
                "document.querySelector('#usercheck_title_div')",
                timeout=20000,
            )
            if page.get_by_text("Network Access Granted", exact=True).count():
                print("Portal already grants network access.", flush=True)
                return
            username_field = page.locator("#LoginUserPassword_auth_username")
            if username_field.count() == 0:
                raise RuntimeError("Portal sign-in form was not found.")
            username_field.fill(username)
            page.locator("#LoginUserPassword_auth_password").fill(password)
            page.evaluate("oAuthentication.submitActiveForm()")
            try:
                page.get_by_text("Network Access Granted", exact=True).wait_for(timeout=20000)
            except PlaywrightTimeoutError as exc:
                error = page.locator("#LoginUserPassword_error_message").inner_text().strip()
                raise RuntimeError(error or "Portal did not confirm login within 20 seconds.") from exc
            print("SRMIST login completed.", flush=True)
        finally:
            browser.close()


def main():
    username, password = credentials()
    failures = 0
    next_attempt = 0
    state = None
    print("Monitoring srmist Wi-Fi every 15 seconds. Press Ctrl+C to stop.", flush=True)
    while True:
        if not wifi_connected():
            current = "away"
            failures = 0
        elif internet_works():
            current = "online"
            failures = 0
        else:
            current = "offline"
            failures += 1
            if failures >= 2 and time.monotonic() >= next_attempt:
                next_attempt = time.monotonic() + RETRY_INTERVAL
                try:
                    login(username, password)
                except Exception as exc:
                    print(f"Login attempt failed: {exc}", file=sys.stderr, flush=True)
        if current != state:
            print({"away": "Not on srmist Wi-Fi.", "online": "Internet access is working.", "offline": "Internet probe failed."}[current], flush=True)
            state = current
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
    except Exception as exc:
        print(f"Monitor stopped: {exc}", file=sys.stderr)
        sys.exit(1)
