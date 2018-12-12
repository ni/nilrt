#!/bin/bash

vmimage="$1"
if [ -z "$vmimage" ]; then
	echo "Usage: $0 <image-name>"
	exit 1
fi

config_present=$(echo "
run
mount /dev/sda3 /
exists /ni-rt.ini" | guestfish -a "$vmimage")

if [ "$config_present" = "true" ]; then
	echo "
	run
	mount /dev/sda3 /
	download /ni-rt.ini /tmp/ni-rt.ini
	! sed -i 's/ConsoleOut\.enabled="False"/ConsoleOut\.enabled="True"/' /tmp/ni-rt.ini
	upload /tmp/ni-rt.ini /ni-rt.ini" | guestfish -a "$vmimage"
fi

echo "
run
mount /dev/sda2 /
download /grub/grubenv /tmp/grubenv
! grub-editenv /tmp/grubenv set consoleoutenable=True
upload /tmp/grubenv /grub/grubenv" | guestfish --pipe-error -a "$vmimage"
