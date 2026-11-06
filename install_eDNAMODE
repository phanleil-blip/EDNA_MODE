#!/usr/bin/env python3
import ast
import getpass
import os
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_URL = "https://github.com/phanleil-blip/EDNA_MODE.git"
WITTY_URL = "https://www.uugear.com/repo/WittyPi4/install.sh"

HOTSPOT_SSID = "eDNAMODE"
HOTSPOT_CONN = "eDNAMODE-hotspot"

HOME = Path.home()
APP_DIR = HOME / "EDNA_MODE"

SERVICE = """[Unit]
Description=eDNA sampler
After=network.target

[Service]
User={user}
WorkingDirectory={app_dir}
ExecStart={app_dir}/venv/bin/python app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""


def run(*cmd, **kwargs):
    subprocess.run(cmd, check=True, **kwargs)


def ask(question):
    return input(f"{question} [y/N] ").strip().lower().startswith("y")


def install_packages():
    try:
        model = Path("/proc/device-tree/model").read_bytes()
    except FileNotFoundError:
        model = b""
    gpio_pkg = "python3-rpi-lgpio" if b"Raspberry Pi 5" in model else "python3-rpi.gpio"

    print("==> Installing system packages")
    run("sudo", "apt-get", "update")
    run("sudo", "apt-get", "install", "-y", "git", "python3-venv", "i2c-tools", gpio_pkg)

    print("==> Enabling I2C")
    run("sudo", "raspi-config", "nonint", "do_i2c", "0")
    run("sudo", "usermod", "-aG", "i2c,gpio", getpass.getuser())


def install_witty_pi():
    if (HOME / "wittypi").exists():
        return
    if not ask("Install the Witty Pi 4 software? (mount the hat first)"):
        return
    script = Path("/tmp/wittypi_install.sh")
    urllib.request.urlretrieve(WITTY_URL, script)
    run("sudo", "sh", str(script))


def get_code():
    print("==> Getting the code")
    if (APP_DIR / ".git").exists():
        # Fails if logs/config.json were changed locally; harmless, the existing copy is kept
        subprocess.run(["git", "-C", str(APP_DIR), "pull", "--ff-only"])
    else:
        run("git", "clone", REPO_URL, str(APP_DIR))


def top_level_names(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name).split(".")[0] for a in node.names)
    return names


def check_repo():
    # Catches syntax errors and imports of names a file doesn't define, before the app is run
    files = {p.stem: p for p in APP_DIR.glob("*.py")}
    files.update({f"hardware.{p.stem}": p for p in (APP_DIR / "hardware").glob("*.py")})

    trees = {}
    for name, path in files.items():
        try:
            trees[name] = ast.parse(path.read_text(), str(path))
        except SyntaxError as e:
            print(f"WARNING: syntax error in {path.relative_to(APP_DIR)}, line {e.lineno}")

    problems = len(files) - len(trees)
    for name, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in trees:
                missing = {a.name for a in node.names} - top_level_names(trees[node.module])
                if missing:
                    problems += 1
                    print(f"WARNING: {files[name].name} imports {', '.join(sorted(missing))} "
                          f"from {node.module}, which doesn't define it")
    return problems > 0


def install_python_libs():
    print("==> Installing Python libraries")
    run("python3", "-m", "venv", "--system-site-packages", str(APP_DIR / "venv"))
    run(str(APP_DIR / "venv/bin/pip"), "install", "flask", "adafruit-circuitpython-mcp230xx")


def setup_service():
    if not ask("Start the sampler automatically at boot?"):
        return
    unit = SERVICE.format(user=getpass.getuser(), app_dir=APP_DIR)
    run("sudo", "tee", "/etc/systemd/system/edna.service",
        input=unit, text=True, stdout=subprocess.DEVNULL)
    run("sudo", "systemctl", "daemon-reload")
    run("sudo", "systemctl", "enable", "edna.service")


def setup_hotspot():
    if not shutil.which("nmcli"):
        return False
    if not ask("Create a Wi-Fi hotspot so the sampler works without another network?"):
        return False
    password = getpass.getpass("Hotspot password (8+ characters): ")
    if len(password) < 8:
        print("Password too short, skipping hotspot.", file=sys.stderr)
        return False

    subprocess.run(["sudo", "nmcli", "connection", "delete", HOTSPOT_CONN],
                   stderr=subprocess.DEVNULL)
    # Low priority so a known Wi-Fi network wins when one is in range
    run("sudo", "nmcli", "connection", "add", "type", "wifi", "ifname", "wlan0",
        "con-name", HOTSPOT_CONN, "ssid", HOTSPOT_SSID,
        "autoconnect", "yes", "connection.autoconnect-priority", "-10",
        "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg",
        "ipv4.method", "shared", "ipv6.method", "ignore",
        "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.proto", "rsn",
        "wifi-sec.pairwise", "ccmp", "wifi-sec.group", "ccmp",
        "wifi-sec.psk", password)
    return True


def main():
    if os.geteuid() == 0:
        sys.exit("Run this as your normal user, not with sudo.")

    install_packages()
    install_witty_pi()
    get_code()
    has_problems = check_repo()
    install_python_libs()
    setup_service()
    hotspot = setup_hotspot()

    if has_problems:
        print("\nFix the warnings above in the repo, then run: git pull")

    print(f"""
Done. Reboot so the I2C and group changes take effect:
    sudo reboot

Then check the boards show up (expect 20 and 21, plus 08 with the Witty Pi):
    i2cdetect -y 1

Run the app by hand:
    sudo systemctl stop edna    # only if start at boot is enabled
    cd {APP_DIR} && source venv/bin/activate && python app.py

Open http://{socket.gethostname()}.local:5000 from a device on the same network.""")
    if hotspot:
        print(f"Or join the '{HOTSPOT_SSID}' Wi-Fi and open http://10.42.0.1:5000")
        print(f"Start the hotspot now with: sudo nmcli connection up {HOTSPOT_CONN}")


if __name__ == "__main__":
    main()
