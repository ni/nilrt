#!/usr/bin/env python2

import pexpect
import sys, os, time, subprocess

if len(sys.argv) < 5:
    print "Usage: %s <feed-server-uri> <recovery_iso> <hdd_image_name> <hdd_image_size>" % sys.argv[0]
    print "Example: %s http://nickdanger.amer.corp.natinst.com/feeds NI_RECOVERY_IMG-cd.iso testimg.img 3G" % sys.argv[0]
    exit(1)

feedserver     = sys.argv[1]
recovery_iso   = sys.argv[2]
hdd_image_name = sys.argv[3]
hdd_image_size = sys.argv[4]

test_timeout = 3600 #seconds

def waitfornetwork():
    print "Waiting for network interface"
    #force target to get an ip after boot to avoid a qemu bug where the IP
    #is not correctly set while booting (reproduced in qemu 2.1 and 2.8)
    child.sendline('dhclient eth0')
    child.expect('# ')
    child.sendline("while ! ifconfig | grep -q 'inet addr.*Bcast'; do sleep 5; done")
    child.expect("# ")

print "Creating virtual hdd image"
os.system("qemu-img create -f raw %s %s" % (hdd_image_name, hdd_image_size))

print "Provisioning virtual hdd image with newer nilrt OS, this may take a while"

enable_kvm = subprocess.check_output(["id | grep -q kvm && echo '-enable-kvm -cpu kvm64' || echo ''"], shell=True)
child = pexpect.spawn ("qemu-system-x86_64 %s -nographic -m 1024 -hda %s -cdrom %s"
                       % (enable_kvm, hdd_image_name, recovery_iso), timeout=test_timeout)

child.expect('Do you want to continue?')
child.sendline('y')
child.expect('Do you want to continue?')
child.sendline('y')
child.expect('Please eject the installation media and restart the system')
child.sendline()

child.expect('NI.* login:')
child.sendline('root')

waitfornetwork()

print "Installing backwards migration package"
child.sendline('opkg update')
child.expect('# ')
child.sendline('opkg install migrate-nilrt')

# prevent auto-reboot to be able to enable safemode console out below
child.expect('# ')
child.sendline('sed -i -e /reboot/d /sbin/ni_migrate_target')

print "Starting bacwards migration to the older nilrt OS, this may take a while"
child.expect('# ')
child.sendline('ni_migrate_target')
child.expect('To continue type YES:')
child.sendline('YES')

# force the provisioned safemode to enable console out b/c we don't have hw button
child.expect('# ')
child.sendline('sed -i -e "s/consoleoutenable=False/consoleoutenable=True/" /boot/.oldNILinuxRT/safemode_files/grub.cfg')
child.expect('# ')
child.sendline('reboot')

child.expect('NI Linux Real-Time \(safe mode on')
child.expect('NI.* login:')
child.sendline('admin')
child.expect('Password: ')
child.sendline()

waitfornetwork()

print "Installing forwards migration package"
# install migration feed manually on older nilrt versions; this needs to be removed once exports
# are generated containing images with the feed added by default
child.sendline("echo 'src/gz images-all-x64 %s/Migration/all/all' >> /etc/opkg/opkg.conf" % feedserver)
child.expect('# ')
child.sendline('opkg update')
child.expect('# ')
child.sendline('opkg install migrate-nilrt')

print "Starting forwards migration to the newer nilrt OS, this may take a while"
child.expect('# ')
child.sendline('ni_migrate_target')
child.expect('To continue type YES:')
child.sendline('YES')

child.expect('NI.* login:')
child.sendline('root')

print "Migration completed succesfully, shutting down and cleaning up"
child.expect('# ')
child.sendline('poweroff')
child.expect('Power down')
child.close()
os.remove(hdd_image_name)
