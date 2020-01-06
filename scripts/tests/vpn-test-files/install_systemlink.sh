#!/bin/bash
set -eEu

target="$1"
tarball="$2"

sshcmd="sshpass -p 1234 ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"

echo "=== Checking target boot mode and architecture."
boot_arch=$($sshcmd admin@$target "uname -m")
if [ $boot_arch != "x86_64" ]; then
	echo "ERROR: don't understand arch '$boot_arch'."
	exit 1
fi

echo "=== Checking target is booted in safemode."
detect_safemode_cmds=(
	'if [[ -e /etc/natinst/safemode ]]; then printf "safemode";'
	'else printf "runmode"; fi; '
)
boot_mode=$($sshcmd admin@$target "${detect_safemode_cmds[*]}")
if [ $boot_mode != "safemode" ]; then
	echo "ERROR: Target must be booted into safemode with ssh enabled."
	exit 1
fi

echo "=== Installing rootfs."
tar xOf "$tarball" ./data.tar.gz \
	| $sshcmd admin@$target 'tar xz -C /mnt/userfs'

echo "=== Running postinst."
tar xOf "$tarball" ./postinst \
	| $sshcmd admin@$target 'cat > /mnt/userfs/tmp/postinst && /bin/bash /mnt/userfs/tmp/postinst'

echo "=== Done."
