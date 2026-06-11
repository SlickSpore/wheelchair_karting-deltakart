echo "===   ©   Wheelchair Karting® 2026     ==="
echo " *                                       *"
echo " *     DeltaKart Firmware Installer      *"
echo " *                                       *"
echo "====== Written by Ettore Caccioli ========"
echo "\n[+] Generating/Updating Startup File"

set -e

CWD=$(pwd)

KART_SERVICE="kart.service"
AP_SERVICE="ap_start.service"

TARGET="gunicorn -c web/gunicorn_config.py web.app:app -w 1 -b 0.0.0.0:8000"

SERVICE_NAME="Wheelchair Karting® Delta Kart Core's Service"
KART_SERVICE_PATH="/etc/systemd/system/$KART_SERVICE"
KART_SERVICE_CONTENT="[Unit]\nDescription=$SERVICE_NAME\nAfter=network.target\n\n[Service]\nExecStart=$TARGET\nRestart=always\nUser=root\nGroup=root\nWorkingDirectory=$CWD\nStandardOutput=journal\nStandardError=journal\n\n[Install]\nWantedBy=multi-user.target\n"

SERVICE_NAME="Wheelchair Karting® Access Point Startup Service"
KART_AP_PATH="/etc/systemd/system/$AP_SERVICE"
KART_AP_CONTENT="[Unit]\nDescription=$SERVICE_NAME\nAfter=network.target\nWants=network.target\n\n[Service]\nType=forking\nExecStart=$CWD/web/access_point/ap_start.sh\nTimeoutStartSec=30\nRemainAfterExit=yes\n\n[Install]\nWantedBy=multi-user.target\n"

echo $KART_SERVICE_CONTENT > $KART_SERVICE_PATH
echo $KART_AP_CONTENT > $KART_AP_PATH

systemctl enable $KART_SERVICE
systemctl enable $AP_SERVICE

echo "[+] Install Process Done!"