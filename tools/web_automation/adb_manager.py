"""
adb_manager.py
──────────────
Central ADB helper.  All phone commands go through here.

Requirements:
    pip install (none — uses subprocess + adb from PATH)

Setup (one-time):
    USB  : Enable Developer Options → USB Debugging on phone. Plug in.
    Wi-Fi: adb tcpip 5555  →  adb connect <phone-ip>:5555
"""

import subprocess
import re
from typing import Optional


# ── ADB binary path (update if adb is not in PATH) ───────────────────────
ADB = "adb"


# ── Result wrapper ────────────────────────────────────────────────────────
class ADBResult:
    def __init__(self, ok: bool, output: str = "", error: str = ""):
        self.ok = ok
        self.output = output
        self.error = error

    def __str__(self):
        return self.output if self.ok else f"ADB error: {self.error}"


# ── Core runner ───────────────────────────────────────────────────────────
def _run(cmd: list[str], timeout: int = 10) -> ADBResult:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return ADBResult(ok=True, output=result.stdout.strip())
        return ADBResult(ok=False, error=result.stderr.strip() or result.stdout.strip())
    except FileNotFoundError:
        return ADBResult(
            ok=False,
            error=(
                "adb not found. Install Android Platform Tools:\n"
                "  Windows : https://developer.android.com/tools/releases/platform-tools\n"
                "  Linux   : sudo apt install adb\n"
                "  Mac     : brew install android-platform-tools"
            ),
        )
    except subprocess.TimeoutExpired:
        return ADBResult(ok=False, error="ADB command timed out.")
    except Exception as e:
        return ADBResult(ok=False, error=str(e))


# ── Device detection ──────────────────────────────────────────────────────
def get_devices() -> list[str]:
    """Return list of connected device serials."""
    r = _run([ADB, "devices"])
    if not r.ok:
        return []
    lines = r.output.splitlines()[1:]          # skip header
    return [
        line.split()[0]
        for line in lines
        if line.strip() and "offline" not in line and "unauthorized" not in line
    ]


def get_primary_device() -> Optional[str]:
    devices = get_devices()
    return devices[0] if devices else None


def is_phone_connected() -> bool:
    return bool(get_devices())


def connect_wifi(ip: str, port: int = 5555) -> ADBResult:
    return _run([ADB, "connect", f"{ip}:{port}"])


# ── Shell helper ──────────────────────────────────────────────────────────
def shell(command: str, device: Optional[str] = None) -> ADBResult:
    device = device or get_primary_device()
    if not device:
        return ADBResult(
            ok=False,
            error=(
                "No Android device connected.\n"
                "• USB : plug in phone with USB Debugging enabled\n"
                "• Wi-Fi: send 'connect phone <ip>' first"
            ),
        )
    return _run([ADB, "-s", device, "shell", command])


# ── Intent launcher ───────────────────────────────────────────────────────
def launch_intent(
    action: str = "",
    package: str = "",
    data_uri: str = "",
    extras: dict | None = None,
    device: Optional[str] = None,
) -> ADBResult:
    cmd = "am start"
    if action:
        cmd += f" -a {action}"
    if data_uri:
        cmd += f" -d '{data_uri}'"
    if package:
        cmd += f" -n {package}"
    if extras:
        for k, v in extras.items():
            cmd += f" --es {k} '{v}'"
    return shell(cmd, device)


# ── Volume / brightness ───────────────────────────────────────────────────
def set_volume(level: int, stream: int = 3) -> ADBResult:
    """stream 3 = media, 2 = ring, 4 = alarm"""
    level = max(0, min(100, level))
    return shell(f"media volume --stream {stream} --set {level}")


def get_volume() -> ADBResult:
    return shell("media volume --stream 3 --get")


def set_brightness(level: int) -> ADBResult:
    """level 0-255"""
    level = max(0, min(255, level))
    # disable auto-brightness first
    shell("settings put system screen_brightness_mode 0")
    return shell(f"settings put system screen_brightness {level}")


def get_brightness() -> ADBResult:
    return shell("settings get system screen_brightness")


# ── Screen control ────────────────────────────────────────────────────────
def wake_screen() -> ADBResult:
    return shell("input keyevent KEYCODE_WAKEUP")


def lock_screen() -> ADBResult:
    return shell("input keyevent KEYCODE_SLEEP")


def unlock_screen(pin: str = "") -> ADBResult:
    wake_screen()
    if pin:
        shell("input keyevent 82")   # MENU → shows unlock prompt
        return shell(f"input text {pin}")
    return shell("input keyevent 82")