import os, subprocess

STARTER_PATH = "/etc/systemd/system/kart.service"

WKDIR = os.getcwd() 
# TARGET = "/gui/main_display.py"
TARGET = "/web/app.py"

SERVICE_FILE = f"""
[Unit]
Description=Kart Control Core
After=network.target

[Service]
ExecStart=/usr/bin/python3 {WKDIR+TARGET}
Restart=always
User=root
WorkingDirectory={WKDIR}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target

"""

def generate_startup_file():
    with open(STARTER_PATH, "w+") as f:
        f.write(SERVICE_FILE)
    f.close()

def install_file():
    subprocess.run(["sudo","systemctl","daemon-reload"])
    subprocess.run(["sudo","systemctl","enable", "kart.service"])
    subprocess.run(["sudo","systemctl","start", "kart.service"])

if __name__ == "__main__":
    print("===   Copyright @ Wheelchair Karting®   ===")
    print(" *                                       *")
    print(" *       Kart Firmware Installer         *")
    print(" *                                       *")
    print("===     Written by Ettore Caccioli      ===")
    print("\n[+] Generating/Updating Startup File")
    generate_startup_file()
    print("[+] Installing Startup File")
    install_file()
    print("[+] Install Done!")