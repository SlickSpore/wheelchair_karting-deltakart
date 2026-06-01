# Access Point Start Routine © 2026 Wheelchair Karting

DEVICE="wlan0"

SSID="DeltaKart105"
PASS="deltakart105"

nmcli r $DEVICE on
nmcli dev wifi hotspot ifname $DEVICE ssid $SSID password $PASS
