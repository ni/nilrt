#!/bin/bash

tarball="$1"
target="$2"
serverip="$3"

mkdir cfgdir
tar -xf "../vpn-test-files/$tarball" -C cfgdir
sed -ien "s/^remote .* 8154/remote $serverip 8154/" ./cfgdir/*.conf
tar -czf payload.tar.gz -C cfgdir .
rm -r cfgdir

openvpn_path="/etc/natinst/share/openvpn"

export SSHPASS=$'\n'
sshcmd="sshpass -e ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"

$sshcmd admin@$target "rm -rf $openvpn_path; mkdir -p $openvpn_path"
cat payload.tar.gz | $sshcmd admin@$target "tar xz -C $openvpn_path"
$sshcmd admin@$target "chown -R openvpn.openvpn $openvpn_path"
