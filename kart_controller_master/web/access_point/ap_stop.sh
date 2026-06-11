#!/bin/bash
set -e

IFACE="wlan0"
SSID=""
PASS=""

systemctl stop ap_start.service
systemctl stop kart.service

pkill hostapd 2>/dev/null || true
pkill dnsmasq 2>/dev/null || true

systemctl start NetworkManager

nmcli radio wifi on
nmcli dev set "$IFACE" managed yes

ip link set "$IFACE" down
ip addr flush dev "$IFACE"
iw dev "$IFACE" set type managed 2>/dev/null || true
ip link set "$IFACE" up

nmcli dev wifi rescan ifname "$IFACE"
sleep 2

nmcli connection delete tempwifi 2>/dev/null || true

nmcli connection add type wifi ifname "$IFACE" con-name tempwifi ssid "$SSID"
nmcli connection modify tempwifi wifi-sec.key-mgmt wpa-psk
nmcli connection modify tempwifi wifi-sec.psk "$PASS"
nmcli connection up tempwifi
