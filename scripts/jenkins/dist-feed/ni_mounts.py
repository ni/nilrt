#!/usr/bin/env python3
import re
import shlex
import os
from pathlib import Path

ENV_MOUNT_PREFIXES = ['MNT', 'NAS']


# CLASSES #
###########

class Mount():
    def __init__(self, spec, file, vfstype, mntopts, freq, passno):
        self.spec = Path(spec)
        self.file = file
        self.vfstype = vfstype
        if all(isinstance(o, str) for o in mntopts):
            self.mntopts = list(mntopts)
        else:
            raise ValueError('mntopts must be an iterable of strings')
        self.freq = int(freq)
        self.passno = int(passno)

        self.is_read_only()  # invoke this method to error if no r/w permissions

    @staticmethod
    def gen_mount_from_fstab_entry(fstab_entry):
        words = shlex.split(fstab_entry)
        words[3] = words[3].split(',')
        vfstype = words[2]
        if vfstype == 'cifs':
            del words[2]
            return MountCIFS(*words)
        else:
            return Mount(*words)

    def is_remote_mount(self):
        raise NotImplementedError

    def is_read_only(self):
        if 'ro' in self.mntopts:
            return True
        elif any(s in self.mntopts for s in ['rw', 'defaults']):
            return False
        else:
            raise RuntimeError('Mount configuration invalid. Does not contain read/write permissions option.')

    def __str__(self):
        return str(self.__dict__.items())

class MountCIFS(Mount):
    RE_UNC = re.compile(r'^//(?P<server>[^/]*)/(?P<share>[^/]*)')

    def __init__(self, spec, file, mntopts, freq, passno):
        super().__init__(spec, file, 'cifs', mntopts, freq, passno)
        self.server, self.share = self.share_tuple()

    def is_remote_mount(self):
        return True

    def share_tuple(self):
        m = self.RE_UNC.match(str(self.spec))
        if m is None:
            raise ValueError('CIFS Mount UNC spec malformed.')
        m = m.groupdict()  # required for python3.4 support
        return (m['server'], m['share'])


# METHODS #
###########

def locate_network_mount(remote_path, env_mount_prefixes=ENV_MOUNT_PREFIXES,
                         check_mount=False, re_spec_match=None):
    """Tries to intuit the location of a network mount.

    Uses environment variables and /proc/mount to try and guess the location of
    network mounts.

    Environment variables are of the format $PREFIX_REMOTE_MOUNT_PATH. Like:
        MNT_BALTIC_PENGUINEXPORTS or NAS_NIRVANA_TEMP

    Args:
        remote_path: iter(str) of path elements to the remote file.
        env_mount_prefixes: iter(str) of environment variable prefixes from
            which to construct standardized mount location variables. Prefixes
            matches from earlier in the list are preferred.
        check_mount: If True, check if the guessed mount location is a real
            mount location. Error if it is not or if it does not exist.
        re_spec_match: str, re.Pattern, or None of regex pattern to match
            against all network mounts. If None; the remote path elements will
            be combined to guess a path.
    Raises:
        FileNotFoundError: check_mount was asserted and the determined mount
            location is not a file.
        RuntimeError: check_mount was asserted and the determined mount
            location is not a mount point.
    """
    # FIRST check env variables
    env_var_base = '_'.join([word.upper() for word in remote_path])
    env_vars = ['%s_%s' % (prefix, env_var_base) for prefix in env_mount_prefixes]

    env_mount = None
    env_mount_location = None
    for var in env_vars:
        try:
            env_mount_location = os.environ[var]
            env_mount = var
        except KeyError:
            continue
        else:
            break

    if check_mount and env_mount_location is not None:
        if not any(*[os.path.samefile(nm.file, env_mount_location) for nm in read_network_mounts()]):
            raise RuntimeError('ENV Mount location %s=%s is not mounted.'
                               % (env_mount, env_mount_location))

    if env_mount_location is not None: return env_mount_location

    # ELSE guess network mounts directly
    if re_spec_match is None:
        re_spec_match = ('\/'.join(remote_path))
    # We have to do this weird type-checking to support python3 installs older
    # than 3.5, because they changed the type of regex compiled patterns over
    # that boundary.
    if not isinstance(re_spec_match, type(re.compile(''))):
        re_spec_match = re.compile(re_spec_match)

    for net_mount in read_network_mounts():
        if re_spec_match.match(str(net_mount.spec)):
            return net_mount.file

    return None

def locate_network_mount_penguinExports(**kwargs):
    kwargs['re_spec_match'] = re.compile(r'//baltic.*/penguinExports(/|$)')
    return locate_network_mount(['baltic', 'penguinExports'], **kwargs)

def locate_network_mount_perforceExports(**kwargs):
    kwargs['re_spec_match'] = re.compile(r'//nirvana.*/perforceExports(/|$)')
    return locate_network_mount(['baltic', 'perforceExports'], **kwargs)

def read_mounts():
    mounts = []
    with open('/proc/mounts', 'r') as fp_mounts:
        mount_entries = fp_mounts.readlines()

    for entry in mount_entries:
        mounts.append(Mount.gen_mount_from_fstab_entry(entry))
    return mounts

def read_network_mounts():
    mounts = read_mounts()

    network_mounts = []
    for mount in mounts:
        try:
            if mount.is_remote_mount():
                network_mounts.append(mount)
        except NotImplementedError: pass

    return network_mounts


# CLI #
#######

if __name__ == "__main__":
    import sys

    from pprint import pprint
    for mount in read_network_mounts():
        pprint(mount.__str__())

    pprint(locate_network_mount_penguinExports())
    pprint(locate_network_mount_perforceExports())
