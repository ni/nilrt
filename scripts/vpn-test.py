#!/usr/bin/env python3
#
# To run this test you need a network bridge setup. An example how to setup a bridge adapter:
#     ip link add name br0 type bridge
#     ip link set br0 up
#     ip link set enp0s25 master br0
#     ip link set enp0s25 up promisc on
#     dhcpcd -q -4 -w br0
#
# The test also requires QEMU have access to the bridge:
#     echo "allow br0" > /etc/qemu/bridge.conf
#

import sys, os, time, subprocess, glob, re, pexpect

FOO_PASS = '1234'

RE_PASSWD_NIAUTH_OLD = re.compile(b'Enter current NIAuth password: ')
RE_PASSWD_NIAUTH_NEW = re.compile(b'(Re-enter|Enter) new NIAuth password: ')
RE_PASSWD_NEW = re.compile(b'(Retype new|New) password: ')
RE_PSTTY = re.compile(b'(\(safemode\) )?\S+@\S+:.*# ')

if len(sys.argv) < 2:
    print("Usage: %s <network-bridge> <nilrt-export-path>" % sys.argv[0])
    print("Example: %s br0 $BALTIC_MNT/penguinExports/nilinux/os-common/export/7.0" % sys.argv[0])
    exit(1)

test_timeout = 900 #seconds = 15 min


def login(vm, user, password):
    """
    Login into the VM
    """
    vm.expect("login: ", timeout=test_timeout)
    vm.sendline(user)
    vm.expect("Password: ", timeout=test_timeout)
    vm.sendline(password)
    vm.expect("# ")

def get_ip_addr(vm):
    """
    Returns the first ip address as ordered by ip addr
    """
    time.sleep(15)
    vm.sendline("ip addr")
    vm.expect("# ")
    return str(re.findall(b'inet [0-9]+(?:\.[0-9]+){3}', vm.before)[1][5:], 'utf-8')

def start_vpn_client(vm):
    """
    Enable the vpn client, print & return its assigned ip
    """
    print("Starting VPN on client")
    vm.sendline('/etc/init.d/vpn start')
    vm.expect("# ")
    time.sleep(15)

def vm_chroot(vm, chroot_path):
    vm.sendline('chroot %s' % chroot_path)
    vm.expect('# ')

def vm_test_command(vm, cmd, output_test_str):
    """
    Run cmd on vm and verify if output_test_str is in the cmd output
    Returns a `match` object
    """
    vm.sendline(cmd)
    vm.expect("# ")
    return re.search(output_test_str, vm.before)

def vm_test_vpn_ping(vm, vpn_ip):
    """
    Ping VPN IP from vm test
    """
    print("Testing VPN ping")
    if not vm_test_command(vm, "ping -c 1 %s" % vpn_ip, b", 0% packet loss"):
        print("ERROR: Couldn't ping client from server")
        cleanup()
        exit(1)

def check_dhcp_ip_range(vm):
    """
    Verify the DHCP assigned IP range doesn't conflict with the VPN IP range
    """
    print("Testing bridge DHCP issued IPs are different from VPN IP")
    cmd = "[ $(ip addr | grep 'inet 10.8.0.' | wc -l) -eq 1 ] && echo DIFFERENT"
    if not vm_test_command(vm, cmd, b"DIFFERENT"):
        print("ERROR: Multiple IPs in the 10.8.0.1/24 range have been issued")
        print("       Use another VPN IP range or check with your administrator")
        cleanup()
        exit(1)

def enable_ssh(vm):
    """
    Given a NILRT vm, enable SSH via ni-rt.ini and start sshd
    """
    vm.sendline("sed -i 's/sshd.enabled=\"False\"/sshd.enabled=\"True\"/' /etc/natinst/share/ni-rt.ini")
    vm.expect("# ")
    vm.sendline("/etc/init.d/sshd start")
    vm.expect("# ")

def vm_set_passwd(vm, new, user='', old=''):
    cases = [
        RE_PASSWD_NIAUTH_OLD,
        RE_PASSWD_NIAUTH_NEW,
        RE_PASSWD_NEW,
        RE_PSTTY,
        ]
    vm.sendline('passwd %s' % user)

    for prompt_iter in range(0, 5):
        case = vm.expect(cases)
        if case == 0:
            vm.sendline(old)
        elif case in (1,2):
            vm.sendline(new)
        elif case == 3:
            break

def cleanup():
    print("Cleaning up")
    os.system("cd ../; rm -rf %s-qemu" % img_name)

net_bridge = sys.argv[1]
export_path = sys.argv[2]

latest_export = max(glob.glob(os.path.join(export_path, '*')), key=os.path.getctime)
img_name = "nilrt-vm-cg-x64"
image_path = "%s/targets/linuxU/x64/gcc-4.7-oe/release/%s-qemu.zip" % (latest_export, img_name)

print("Fetching VM image from: %s" % image_path)
os.system("rm -rf %s-qemu" % img_name)
os.system("unzip -q %s" % image_path)
os.chdir("%s-qemu" % img_name)

print("Booting VPN client VM")
client_mac_address="52:54:d7:38:5c:e8"
client = pexpect.spawn ("../vpn-test-files/start_qemu_bridge.sh %s %s.qcow2 %s" %
                        (net_bridge, img_name, client_mac_address), timeout=test_timeout)

print("Booting VPN server VM")
server_mac_address="52:54:d7:38:5c:e9"
server = pexpect.spawn ("../vpn-test-files/start_qemu_bridge.sh %s %s.qcow2 %s" %
                        (net_bridge, img_name, server_mac_address), timeout=test_timeout)

# create log files
fp_log_client = open('client.log', 'wb')
client.logfile = fp_log_client
fp_log_server = open('server.log', 'wb')
server.logfile = fp_log_server


login(client, "admin", "")
client_ip = get_ip_addr(client)
print("Client bridge IP: %s" % client_ip)

login(server, "admin", "")

vm_set_passwd(server, FOO_PASS, user='admin', old='')
vm_set_passwd(client, FOO_PASS, user='admin', old='')

server_ip = get_ip_addr(server)
print("Server bridge IP: %s" % server_ip)

print("Starting sshd on server")
enable_ssh(server)
print("Starting sshd on client")
enable_ssh(client)

check_dhcp_ip_range(client)
check_dhcp_ip_range(server)

print("Deploying VPN config to client")
os.system('../vpn-test-files/deploy_vpn_config.sh openvpn-client-cfg.tar.gz %s %s' % (client_ip, server_ip))
print("Deploying VPN config to server")
os.system('../vpn-test-files/deploy_vpn_config.sh openvpn-server-cfg.tar.gz %s %s' % (server_ip, server_ip))

print("Starting VPN server daemon")
server.sendline("cd /etc/natinst/share/openvpn; nohup openvpn --config openvpn.conf &")
server.expect("# ")
server.sendline("cd")
server.expect("# ")
print("Server VPN IP: 10.8.0.1")

# VPN client IPs increase monotonically starting from the server IP
client_vpn_ip = "10.8.0.2"
start_vpn_client(client)
print("Client VPN IP: %s" % client_vpn_ip)
vm_test_vpn_ping(server, client_vpn_ip)

print("Installing latest SystemLink image via VPN from")
sl_image_path = glob.glob("%s/distribution-systemlink/release/RT Images/SystemLink/*/systemlink-linux-x64.tar" % latest_export)[0]
print(sl_image_path)

scp_cmd="sshpass -p 1234 scp -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
os.system("%s '%s' admin@%s:" % (scp_cmd, sl_image_path, server_ip))
os.system("%s ../vpn-test-files/install_systemlink.sh admin@%s:" % (scp_cmd, server_ip))

server.sendline("opkg update; opkg install sshpass")
server.expect("# ")
server.sendline("./install_systemlink.sh %s ./systemlink-linux-x64.tar" % client_vpn_ip)
server.expect("=== Done.")
# The systemlink Base Image doesn't have the NIAuth pam module. We won't be
# able to use it to log into runmod. So give the 'root' user in the userfs
# shadow file a dumb password and use it to log in instead.
vm_chroot(client, '/mnt/userfs')
vm_set_passwd(client, FOO_PASS, user='root', old='')
client.sendline('exit')  # can't chain any other commands after 'exit'

print("Finished installing latest SystemLink, waiting for client to reboot")
client.sendline('reboot')
login(client, 'root', FOO_PASS)

print("Sanity checking VPN runmode installation")
if vm_test_command(client, "echo RESULT $(ls /boot/runmode/ | wc -l)", b"RESULT 0"):
    print("ERROR: No runmode files present under /boot/runmode")
    cleanup()
    exit(1)

print("Verifying VPN config file persistence after installation")
if vm_test_command(client, "echo RESULT $(ls /etc/natinst/share/openvpn | wc -l)", b"RESULT 0"):
    print("ERROR: No VPN config files present under /etc/natinst/share/openvpn")
    cleanup()
    exit(1)

start_vpn_client(client)

client.sendline("poweroff")
server.sendline("poweroff")

fp_log_client.close()
fp_log_server.close()

cleanup()
