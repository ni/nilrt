#!/bin/bash

bridge_name="$1"
vm_name="$2"

# This line creates a random MAC address. The downside is the DHCP server will assign a different IP address each time
printf -v macaddr "52:54:%02x:%02x:%02x:%02x" $(( $RANDOM & 0xff)) $(( $RANDOM & 0xff )) $(( $RANDOM & 0xff)) $(( $RANDOM & 0xff ))
# Make sure the macaddr is not already used
while arp-scan --retry=5 --interface br0 --localnet | grep -qi "$macaddr"; do
    printf -v macaddr "52:54:%02x:%02x:%02x:%02x" $(( $RANDOM & 0xff)) $(( $RANDOM & 0xff )) $(( $RANDOM & 0xff)) $(( $RANDOM & 0xff ))
done
# Instead, uncomment and edit this line to set a static MAC address. The benefit is that the DHCP server will assign the same IP address.
# macaddr='52:54:be:36:42:a9'

enable_kvm=$(id | grep -q kvm && echo '-enable-kvm -cpu kvm64' || echo '')

qemu-system-x86_64 -snapshot -nographic $enable_kvm -smp 2 -m 1024 -net nic,macaddr=$macaddr -net bridge,br="$bridge_name" "$vm_name"
