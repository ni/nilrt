#!/usr/bin/env python3
import http.server
import multiprocessing as mp
import os
import pexpect
import re
import shutil
import socket
import stat
import subprocess as sp
import sys
import tempfile
import threading
import zipfile
from time import sleep
from types import SimpleNamespace
from pprint import pprint
from http.server import HTTPServer, SimpleHTTPRequestHandler

import libytest.parse_console


class NILRTFeedServerDaemon(mp.Process):

    def __init__(self, bind_address='127.0.0.1', server_root=os.getcwd()):
        super().__init__()
        self.bind_address = bind_address
        self.root = server_root

        # acquire a random open socket
        self.socket = socket.socket()
        self.socket.bind((self.bind_address, 0))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # start the feed server
        self._ev_run_server = mp.Event()
        self._feed_thread = None

    def __del__(self):
        if self._feed_thread is not None:
            self._server.shutdown()
        if self.socket:
            self.socket.close()

    @property
    def server_port(self):
        try:
            return self.socket.getsockname()[1]
        except AttributeError:
            return None

    def run(self):
        """This method runs in a new process context."""
        os.chdir(self.root)
        self._feed_thread = self

        # Create HTTP Server instance
        self._server = HTTPServer((self.bind_address, self.server_port), SimpleHTTPRequestHandler)
        self._ev_run_server.set()

        # Start the server in its own thread (so that shutdown works.)
        print('Starting feed server on: http://%s:%d/' % (self._server.server_name, self._server.server_port))
        print('Serving root: %s' % self.root)
        self._feed_thread = threading.Thread(target=self._server.serve_forever)
        self._feed_thread.start()

        # Have the daemon thread continuously check that we are 
        while self._ev_run_server.is_set():
            sleep(2)
        self._server.shutdown()

    def stop(self):
        print('Stopping feed server...')
        self._ev_run_server.clear()


class NILRTPtestChild():

    PTEST_FEED_DEVICE_ID = 'ptf'
    PTEST_FEED_NET = '10.0.2.0/24'
    PTEST_FEED_HOST_IPV4 = '10.0.2.2'
    CHILD_TIMEOUT=30

    RE_LOGIN_PASSWORD    = re.compile(b'Password: ')
    RE_LOGIN_USER        = re.compile(b'\S+ login: ')
    RE_PASSWD_NEW        = re.compile(b'(Retype new|New) password: ')
    RE_PASSWD_NIAUTH_NEW = re.compile(b'(Re-enter|Enter) new NIAuth password: ')
    RE_PASSWD_NIAUTH_OLD = re.compile(b'Enter current NIAuth password: ')
    RE_PSTTY             = re.compile(b'(\(safemode\) )?\S+@\S+:.*# ')

    def  __init__(self, spawn_script, guest_cpus=4, guest_memory=4096,
                  logfile=None):
        self.__init_qemu_args()

        # spawn pexpect child process
        script_args = ['-s', '-c', str(guest_cpus), '-m', str(guest_memory),
                       '--']
        if logfile is not None:
            self.logfile = open(logfile, 'wb')
        else:
            self.logfile = None
        self.child = pexpect.spawn(spawn_script,
                        args=script_args + self.qemu_args,
                        timeout=self.CHILD_TIMEOUT,
                        logfile=self.logfile)

    def __del__(self):
        if self.logfile is not None:
            self.logfile.close()

    def __init_qemu_args(self):
        args = []
        args.append('-netdev user,id=%s,net=%s,host=%s' % \
                (self.PTEST_FEED_DEVICE_ID,
                 self.PTEST_FEED_NET,
                 self.PTEST_FEED_HOST_IPV4))
        args.append('-device e1000,netdev=%s' % self.PTEST_FEED_DEVICE_ID)
        self.qemu_args = args

    def interact(self):
        print('Entering interactive mode.')
        self.child.interact()

    def login(self, user, password):
        """
        Login into the VM
        """
        self.child.expect(self.RE_LOGIN_USER, timeout=(5 * self.CHILD_TIMEOUT))
        self.child.sendline(user)
        # switch: nilrt will require a password prompt,
        #         nilrt-nxg will not, if the password is empty
        for retry in range(0, 2):
            case = self.child.expect([self.RE_LOGIN_PASSWORD, self.RE_PSTTY])
            if case == 0:
                self.child.sendline(password)
            else:
                break

    def opkg_install(self, *pkgs, update=True):
        cmd = 'opkg install %s' % ' '.join(pkgs)
        if update:
            cmd = 'opkg update && ' + cmd
        return self.sh_command(cmd)

    def run_ptest_suite(self, *args):
        if len(args) == 0:
            self.sh_command('ptest-runner', timeout=900)
        else:
            for arg in args:
                self.sh_command('ptest-runner %s' % arg, timeout=300)

    def setup_ptest_feeds(self, feed_port):
        self.sh_command('rm -fv /etc/opkg/opkg-signing.conf')
        self.sh_command("sed -i 's/http:\/\/.*\/feeds\/\w\+\/x64/http:\/\/%s:%s/' /etc/opkg/base-feeds.conf" % (self.PTEST_FEED_HOST_IPV4, feed_port))
        self.opkg_install('packagegroup-ni-ptest-smoke', update=True)
        self.sh_command('ptest-runner -l')

    def sh_command(self, cmd, timeout=30):
        """
        Run cmd on vm and verify if output_test_str is in the cmd output
        Returns a `match` object
        """
        self.child.sendline(cmd)
        self.child.expect(self.RE_PSTTY, timeout=timeout)
        return self.child.before

    def reboot(self):
        self.child.sendline('reboot')
        # TODO: be a little nicer here to the VM

    def shutdown(self):
        self.child.sendline('shutdown -h now')
        # TODO: be a little nicer here to the VM


# CLI #
#######

def create_results_dir(path):
    realpath = os.path.realpath(path)
    os.makedirs(realpath, exist_ok=True)
    return realpath

def junit_parse_log(logfile):
    # name the output file the same as the logfile, but with a '.xml' extension
    outfile = os.path.join(os.path.dirname(logfile),
                  os.path.splitext(os.path.basename(logfile))[0] + '.xml')
    print('outfile=%s' % outfile)
    parser_args = SimpleNamespace(**{
        'mask_file': None,
        'verbose': True,
        'verbose_output': True,
        'console_file': [logfile],
        'output_file': outfile,
        })
    pprint(parser_args)
    log_parser = libytest.parse_console.Application(parser_args)
    log_parser.main()

def test_nilrt_ptest(start_script, feed_server_port, guest_cpus, guest_memory,
                    logfile, suites=[]):
    child = NILRTPtestChild(start_script, guest_cpus=guest_cpus,
                guest_memory=guest_memory, logfile=logfile)

    try:
        child.login('root', '')

        child.sh_command('ip route')
        child.sh_command('ip a')

        child.setup_ptest_feeds(feed_server_port)
        child.run_ptest_suite(*suites)
        child.shutdown()
    except pexpect.exceptions.TIMEOUT as e:
        print(e)
        return False
    else:
        return True

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-f', '--feed', nargs=1, action='store', required=True)
    parser.add_argument('-n', '--no-junit-parse', action='store_true')
    parser.add_argument('run_id')
    parser.add_argument('vm_dir')
    parser.add_argument('test_results_dir', default=".")
    args = parser.parse_args()

    # create in the main script context so that it will be cleaned up on exit
    vm_dir_temp = None
    # if the vm_dir is a zipfile, extract it to a tempfile
    if zipfile.is_zipfile(args.vm_dir):
        vm_dir_temp = tempfile.TemporaryDirectory()
        print('Detected vm_dir as zip file. Extracting to: %s' % vm_dir_temp.name)
        with zipfile.ZipFile(args.vm_dir) as zip_vm:
            zip_vm.extractall(path=vm_dir_temp.name)
        # search for a QEMU qcow disk within the archive
        found = False
        for root, dirs, fils in os.walk(vm_dir_temp.name):
            for fil in fils:
                if os.path.splitext(fil)[1] == '.qcow2':
                    args.vm_dir = root
                    found = True
                    break
            if found: break
        # make any scripts in the vm_dir executable for pexpect
        if found:
            for fil in os.listdir(args.vm_dir):
                if os.path.splitext(fil)[1] == '.sh':
                    sc_path = os.path.join(args.vm_dir, fil)
                    mode = os.stat(sc_path).st_mode
                    os.chmod(sc_path, mode | stat.S_IRWXU)
        if not found:
            print('ERROR: could not find qcow2 disk in the vm archive.')
            sys.exit(1)

    # setup the test results dir and log files
    results_dir = create_results_dir(args.test_results_dir)
    child_start_script = os.path.join(args.vm_dir, 'run-nilrt-vm-x64.sh')
    def _child_log(child_name):
        return os.path.join(args.test_results_dir, '%s.log' % child_name)

    # Start the ptest feed server for use by the test children
    feed_server = NILRTFeedServerDaemon(bind_address='127.0.0.1',
                                        server_root=args.feed[0])

    rc = True
    try:
        feed_server.start()  # start the feed server daemon in a new process
        sleep(3)  # give the feed_server a few seconds to setup and get a port

        # test all suites on a resourceful target
        child_log = _child_log('%s-max' % args.run_id)
        print('Starting test child %s. Logging output to: %s' % (args.run_id, child_log))
        rc = test_nilrt_ptest(child_start_script,
                feed_server.server_port, guest_cpus=4, guest_memory=4096,
                logfile=child_log) and rc
        if not args.no_junit_parse:
            junit_parse_log(child_log)

        # test all suites on a minimal target
        child_log = _child_log('%s-min' % args.run_id)
        print('rc=%s' % rc)
        print('Starting test child %s. Logging output to: %s' % (args.run_id, child_log))
        rc = test_nilrt_ptest(child_start_script,
                feed_server.server_port, guest_cpus=1, guest_memory=1024,
                logfile=child_log) and rc
        if not args.no_junit_parse:
            print('rc=%s' % rc)
            junit_parse_log(child_log)
    except KeyboardInterrupt:
        pass
    finally:
        feed_server.stop()  # tell the feed server thread to stop
        feed_server.join()

        sys.exit(0)  # always exit true if the test completes
