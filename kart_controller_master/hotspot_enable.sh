#!/bin/bash

# Set the network interface to be used for the hotspot (e.g., wlan0)
INTERFACE="wlan0"

# Set the SSID (network name) and password for the hotspot
SSID="MyHotspot"
PASSWORD="mysecretpassword"

# Check if nmcli is available
if ! command -v nmcli &> /dev/null
then
    echo "nmcli command not found. Please install NetworkManager."
    exit 1
fi

# Check if the specified interface exists
if ! ip link show "$INTERFACE" &> /dev/null
then
    echo "Interface $INTERFACE not found. Please check your network interface name."
    exit 1
fi

# Disable any active connection on the interface
echo "Disconnecting from any existing network on $INTERFACE..."
nmcli device disconnect "$INTERFACE"

# Set up the hotspot using NetworkManager
echo "Creating hotspot with SSID: $SSID"
nmcli dev wifi hotspot ifname "$INTERFACE" ssid "$SSID" password "$PASSWORD"

# Check if the hotspot was created successfully
if [ $? -eq 0 ]; then
    echo "Hotspot created successfully!"
else
    echo "Failed to create hotspot. Please check your settings."
    exit 1
fi
