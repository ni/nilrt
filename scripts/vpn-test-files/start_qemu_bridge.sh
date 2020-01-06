#!/bin/bash

bridge_name="$1"
vm_name="$2"
vm_mac_address="$3"

if [ -n "$vm_mac_address" ]; then
    macaddr=$vm_mac_address
    # Make sure the macaddr is not already used
    (arp-scan --retry=5 --interface $bridge_name --localnet || exit 1) | grep -qi "$macaddr"
    if [[ $? -eq 0 ]]; then
        echo "ERROR - Supplied mac address is already in use"
        exit 1
    fi
else
    # This line creates a random MAC address. The downside is the DHCP server will assign a different IP address each time
    printf -v macaddr "52:54:%02x:%02x:%02x:%02x" $(( $RANDOM & 0xff)) $(( $RANDOM & 0xff )) $(( $RANDOM & 0xff)) $(( $RANDOM & 0xff ))
    # Make sure the macaddr is not already used
    while (arp-scan --retry=5 --interface $bridge_name --localnet || exit 1) | grep -qi "$macaddr"; do
        printf -v macaddr "52:54:%02x:%02x:%02x:%02x" $(( $RANDOM & 0xff)) $(( $RANDOM & 0xff )) $(( $RANDOM & 0xff)) $(( $RANDOM & 0xff ))
    done
fi

# Instead, uncomment and edit this line to set a static MAC address. The benefit is that the DHCP server will assign the same IP address.
# macaddr='52:54:be:36:42:a9'

./run-${vm_name}.sh \
	-s \
	-c 2 \
	-m 1024 \
	-- \
	-net nic,macaddr=$macaddr \
	-net bridge,br="$bridge_name"
