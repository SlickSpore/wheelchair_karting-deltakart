#!/bin/bash
set -e

# Esporta il PATH corretto in modo che cron trovi tutti i binari di sistema
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

IFACE="wlan0"
IP="10.42.0.1/24"
SUBNET="10.42.0.0/24"
DHCP_RANGE="10.42.0.10,10.42.0.200,12h"

echo "[*] Stopping conflicting services..."
systemctl stop NetworkManager 2>/dev/null || true
systemctl stop wpa_supplicant 2>/dev/null || true
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true

pkill -9 hostapd 2>/dev/null || true
pkill -9 dnsmasq 2>/dev/null || true

# Uso del path assoluto per fuser (spesso in /usr/bin o /sbin)
/usr/bin/fuser -k 67/udp 2>/dev/null || true
/usr/bin/fuser -k 53/udp 2>/dev/null || true

echo "[*] Resetting interface..."
ip link set "$IFACE" down || true
ip addr flush dev "$IFACE" || true

# Attendi un secondo per il reset hardware
sleep 1

echo "[*] Setting AP Mode..."
iw dev "$IFACE" set type __ap

ip link set "$IFACE" up

echo "[*] Assigning static IP..."
ip addr add "$IP" dev "$IFACE"

echo "[*] Enabling IPv4 forwarding..."
sysctl -w net.ipv4.ip_forward=1 >/dev/null

echo "[*] Setting DNS..."
# Evitiamo di rompere i link simbolici di systemd-resolved se attivo
rm -f /etc/resolv.conf
echo "nameserver 1.1.1.1" > /etc/resolv.conf

echo "[*] Starting hostapd..."
/usr/sbin/hostapd /etc/hostapd/hostapd.conf -B

sleep 2

echo "[*] Starting dnsmasq (DHCP)..."
# NOTA: Rimosso il backslash finale e aggiunto il path assoluto
/usr/sbin/dnsmasq \
  --interface="$IFACE" \
  --bind-interfaces \
  --dhcp-authoritative \
  --dhcp-range="$DHCP_RANGE" \
  --dhcp-option=3,10.42.0.1 \
  --dhcp-option=6,1.1.1.1 \
  --no-resolv \
  --log-dhcp

echo "[✓] AP should be up"
