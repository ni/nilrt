#!/usr/bin/env python2

import sys, os, time, subprocess, glob, pexpect

if len(sys.argv) < 3:
    print "Usage: %s <feed-server-uri> <nilrt-export-path>" % sys.argv[0]
    print "Example: %s http://nickdanger.amer.corp.natinst.com/feeds/Migration/all/all $BALTIC_MNT/penguinExports/nilinux/nilrt-oe/lynx/export/19.4" % sys.argv[0]
    exit(1)

def enable_console_out(child):
    child.sendline('cd /boot/.oldNILinuxRT && mkdir payload')

    child.sendline('mv initrd initrd.cpio.gz')
    child.sendline('gzip -d initrd.cpio.gz')
    child.sendline('cd payload')
    child.sendline('export EXTRACT_UNSAFE_SYMLINKS=1 && cpio -idm < ../initrd.cpio')

    child.expect('# ')

    child.sendline('sed -i -e "s/consoleoutenable=False/consoleoutenable=True/" payload/grub.cfg')
    child.sendline('find . | cpio -oH newc > ../initrd.cpio && cd ..')
    child.sendline('gzip initrd.cpio && mv initrd.cpio.gz initrd && rm -rf payload')
    child.sendline('chmod 755 initrd')

    child.expect('# ')

feedserver  = sys.argv[1]
export_path = sys.argv[2]

test_timeout = 3600 #seconds

latest_export = max(glob.glob(os.path.join(export_path, '*')), key=os.path.getctime)
image_path = "%s/images/NILinuxRT-x64/nilrt-vm-x64-qemu.zip" % latest_export

print "Fetching VM image from: %s" % image_path
os.system("rm -rf nilrt-vm-x64-qemu")
os.system("unzip %s" % image_path)
os.chdir("nilrt-vm-x64-qemu")

print "Booting os image"
enable_kvm = subprocess.check_output(["id | grep -q kvm && echo '-enable-kvm -cpu kvm64' || echo ''"], shell=True)
child = pexpect.spawn ("qemu-system-x86_64 %s -nographic -m 1024 -hda %s -netdev user,id=u1 -device e1000,netdev=u1"
                       % (enable_kvm, "nilrt-vm-x64.qcow2"), timeout=test_timeout)

child.expect('NI.* login:')
child.sendline('root')
child.expect('# ')

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
child.expect('# ')

# force the provisioned safemode to enable console out
print "Enable console out and reboot"
enable_console_out(child)
child.sendline('reboot')

child.expect(r'NI Linux Real-Time \(safe mode on')
child.expect('NI.* login:')
child.sendline('admin')
child.expect('Password: ')
child.sendline()
child.expect('# ')

print "Installing forwards migration package"
child.sendline("echo 'src/gz migration-x64 %s' > /etc/opkg/migration.conf" % feedserver)
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
child.expect('# ')

print "Migration completed succesfully, shutting down and cleaning up"
child.sendline('poweroff')
child.expect('Power down')
child.close()
os.chdir('..')
os.system("rm -rf nilrt-vm-x64-qemu")
