#!/usr/bin/env python3

# Authors: Dylan Turner
# Description:
# - Diff feeds of two NI Linux RT releases from their GitHub branches to create a json diff
# - Steps:
#     1. Pull core/ and extra/ feed info from GitHub for branches to compare
#     2. Pull the Packages files from all four feeds
#     3. Parse the package
#     4. Compare the packages to each other
#     5. Generate JSON report

import re
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from requests import get, Response
from json import dumps
from dataclasses import dataclass

# Defines the base URL for feeds
DEF_FEED_BASE: str = 'http://download.ni.com/ni-linux-rt/feeds'

# Constants used for constructing the url to a file on GitHub containing feed information
GITHUB_BASE: str = 'https://raw.githubusercontent.com/ni/meta-nilrt'
GITHUB_CONF_FNAME: str = 'conf/distro/nilrt.conf'
ARCH: str = 'x64'
SUB_FEEDS: list[str] = [ 'x64', 'core2-64', 'all' ]

# If you change the info in the report, update this variable
DATA_STRUCT_VERS = '0'

class PkgDiffError(Exception):
    '''A base class for the custom errors in this script.'''
    pass

class BranchFileNotFoundError(PkgDiffError):
    '''An error for when a file cannot be found in the GitHub repo for a specified branch.'''
    def __init__(self, branch_name: str, file_name: str) -> 'BranchFileNotFoundError':
        super().__init__('Failed to find file \'%s\' in branch %s.' % (branch_name, file_name))

class FeedDoesNotExistError(PkgDiffError):
    '''An error for when the feed corresponding to the specified branch can't be found.'''
    def __init__(self, branch_name: str, feed_name: str) -> 'FeedNotFound':
        super().__init__('Failed to find feed \'%s\' in branch %s.' % (feed_name, branch_name))

class InvalidBranchFileError(PkgDiffError):
    '''An error when there is an issue processing the Makefile containing feed information.'''
    def __init__(self, branch_name: str, file_name: str) -> 'InvalidBranchFile':
        super().__init__(
            'Information in file \'%s\' in branch \'%s\' contained unexpected information.' \
                % (file_name, branch_name)
        )

class UnexpectedError(PkgDiffError):
    '''An error for generic errors for logical problems that could (but shouldn't) happen.'''
    pass

class CLIParser(ArgumentParser):
    '''
    This is a class that inherits from the ArgumentParser to separate the CLI argument logic
    from the main function for more readable code.

    The arguments passed in include the old and new branches to compare along with their version
    numbers. Optionally, one can change the base feed URL
    '''

    def __init__(self) -> 'CLIParser':
        super().__init__(
            description = 'Diff package feeds of two NI Linux RT releases via GitHub branches.',
            epilog =
'''Usage examples:
- example (finding differences between 8.11 and 9.0):
    ./scripts/diff-pkg-changes.py \\
        nilrt/21.8/sumo nilrt/22.5/hardknott \\
        --feed_base http://nickdanger.natinst.com/feeds
- example (updating an existing file):
    ./scripts/diff-pkg-changes.py ... >> ./docs/feed-changelog.json''',
            formatter_class = RawTextHelpFormatter
        )
        self.add_argument(
            'old_branch',
            metavar = 'OLD', type = str,
            help = 'The nilrt branch of the older release'
        )
        self.add_argument(
            'new_branch',
            metavar = 'NEW', type = str,
            help = 'The nilrt branch of the newer release'
        )
        self.add_argument(
            '--feed_base', type = str, default = DEF_FEED_BASE,
            help = 'Optionally set the feed\'s url base'
        )

@dataclass
class Package:
    name: str
    version: str
    depends: str
    provides: str
    replaces: str
    conflicts: str
    recommends: str
    section: str
    architecture: str
    maintainer: str
    md5sum: str
    sha256sum: str
    size: int
    filename: str
    source: str
    description: str
    oe: str
    homepage: str
    license: str
    priority: str

    def diff(self, other: 'Package') -> dict:
        '''
        Compare one package to another and store the result as a dictionary.
        
        Currently the info that is cared about is:
        - Version
        - Depends
        - Replaces
        - Section
        - Size
        '''

        diff_dict = {}

        if self.version != other.version:
            diff_dict['version'] = {
                'old': self.version,
                'new': other.version
            }
        if self.depends != other.depends:
            diff_dict['depends'] = {
                'old': self.depends,
                'new': other.depends
            }
        if self.replaces != other.replaces:
            diff_dict['replaces'] = {
                'old': self.replaces,
                'new': other.replaces
            }
        if self.section != other.section:
            diff_dict['section'] = {
                'old': self.section,
                'new': other.section
            }
        if self.size != other.size:
            diff_dict['size'] = {
                'old': str(self.size),
                'new': str(other.size)
            }

        if diff_dict != {}:
            diff_dict['name'] = self.name

        return diff_dict

def get_feed_and_vers(branch_name: str) -> str:
    '''Get the year/identity of each branch's feed by pulling the info from a file on GitHub.'''

    # Pull the file that defines the feed name from the GitHub repo
    url: str = GITHUB_BASE + '/' + branch_name + '/' + GITHUB_CONF_FNAME
    request: Response = get(url)
    if request.status_code != 200:
        raise BranchFileNotFoundError(branch_name, GITHUB_CONF_FNAME)
    file: str = request.text

    # Get the lines in the file that have the feed info and version info
    feed: str = None
    vers: str = None
    feed_re: re.Pattern = re.compile('^NILRT_FEED_NAME\s*\??=\s*"([^"]*)"$')
    vers_re: re.Pattern = re.compile('^DISTRO_VERSION\s*\??=\s*"([^"]*)"$')
    for line in file.split('\n'):
        feed_match: re.Match = feed_re.match(line)
        if feed_match is not None:
            feed = feed_match.group(1)
        vers_match: re.Match = feed_re.match(line)
        if vers_match is not None:
            vers = vers_match.group(1)
        if feed is not None and vers is not None:
            break

    if feed is None:
        raise InvalidBranchFileError(branch_name, GITHUB_CONF_FNAME)
    if vers is None:
        raise InvalidBranchFileError(branch_name, GITHUB_CONF_FNAME)

    return (feed, vers)

def get_packages(
    feed_url_base: str, feed_version: str, feed_name: str, sub_feed: str, branch_name: str
) -> dict[str, 'Package']:
    '''Pull Packages file from feed and parse it into a list of Package objects.'''

    pkgs: dict[str, 'Package'] = {}

    # Get the package file
    url: str = \
        feed_url_base + '/' + feed_version + '/' + ARCH + '/' + feed_name + '/' \
            + sub_feed + '/Packages'
    request: Response = get(url)
    if request.status_code != 200:
        raise FeedDoesNotExistError(branch_name, feed_name)
    file: str = request.text

    # Parse every package listing
    for pkg_txt in file.split('\n\n'):
        if pkg_txt == '':
            continue

        pkg_dict: dict[str, str] = {}
        for line in pkg_txt.split('\n'):
            if line == '':
                continue
            tokens: list[str] = line.split(': ', maxsplit = 1)
            if len(tokens) < 2:
                raise UnexpectedError(
                    'Unexpected line in Packages file in feed %s for branch %s.' \
                        % (feed_name, branch_name)
                )
            pkg_dict[tokens[0]] = tokens[1]

        try:
            if (pkg_dict['Package'] + '_' + pkg_dict['Architecture']) in pkgs.keys():
                continue
            pkgs[pkg_dict['Package'] + '_' + pkg_dict['Architecture']] = Package(
                pkg_dict['Package'],
                pkg_dict['Version'],
                pkg_dict.get('Depends', ''),
                pkg_dict.get('Provides', ''),
                pkg_dict.get('Replaces', ''),
                pkg_dict.get('Conflicts', ''),
                pkg_dict.get('Recommends', ''),
                pkg_dict['Section'],
                pkg_dict['Architecture'],
                pkg_dict['Maintainer'],
                pkg_dict['MD5Sum'],
                pkg_dict['SHA256sum'],
                int(pkg_dict['Size']),
                pkg_dict['Filename'],
                pkg_dict['Source'],
                pkg_dict['Description'],
                pkg_dict['OE'],
                pkg_dict.get('HomePage', ''),
                pkg_dict['License'],
                pkg_dict['Priority']
            )
        except KeyError:
            raise UnexpectedError(
                'Missing key info in Packages file of feed \'%s\' in branch %s.' \
                    % (feed_name, branch_name)
            )

    return pkgs

def gen_report(
    old_core_pkgs: dict[str, 'Package'], new_core_pkgs: dict[str, 'Package'],
    old_extra_pkgs: dict[str, 'Package'], new_extra_pkgs: dict[str, 'Package'],
    old_vers: str, new_vers: str
) -> dict:
    '''Generate a final report from all the package changes as a dict to be converted into JSON.'''

    # Handle core diffs
    core_pkg_changes: list[dict] = []
    core_pkgs_added: list[dict[str, str]] = []
    core_pkgs_removed: list[dict[str, str]] = []
    for pkg_id, pkg in old_core_pkgs.items():
        other_vers_of_pkg = new_core_pkgs.get(pkg_id, None)
        if other_vers_of_pkg is None:
            core_pkgs_removed.append({
                'name': pkg.name,
                'version': pkg.version
            })
        else:
            diff: dict = pkg.diff(other_vers_of_pkg)
            if diff != {}:
                core_pkg_changes.append(diff)
            new_core_pkgs.pop(pkg_id)
    for pkg_id, pkg in new_core_pkgs.items():
        # We removed packages that were duplicates, so what's left is new packages
        core_pkgs_added.append({
            'name': pkg.name,
            'version': pkg.version
        })

    # Do the same for extra
    extra_pkg_changes: list[dict] = []
    extra_pkgs_added: list[dict[str, str]] = []
    extra_pkgs_removed: list[dict[str, str]] = []
    for pkg_id, pkg in old_extra_pkgs.items():
        other_vers_of_pkg = new_extra_pkgs.get(pkg_id, None)
        if other_vers_of_pkg is None:
            extra_pkgs_removed.append({
                'name': pkg.name,
                'version': pkg.version
            })
        else:
            diff: dict = pkg.diff(other_vers_of_pkg)
            if diff != {}:
                extra_pkg_changes.append(diff)
            new_extra_pkgs.pop(pkg_id)
    for pkg_id, pkg in new_extra_pkgs.items():
        # We removed packages that were duplicates, so what's left is new packages
        extra_pkgs_added.append({
            'name': pkg.name,
            'version': pkg.version
        })

    return {
        'version': DATA_STRUCT_VERS,
        'arch': ARCH,
        'old_nilrt_version': old_vers,
        'new_nilrt_version': new_vers,
        'core': {
            'changes': core_pkg_changes,
            'added': core_pkgs_added,
            'removed': core_pkgs_removed
        }, 'extra': {
            'changes': extra_pkg_changes,
            'added': extra_pkgs_added,
            'removed': extra_pkgs_removed    
        }
    }

def main(args: Namespace) -> int:
    old_branch: str = args.old_branch
    new_branch: str = args.new_branch
    feed_base: str = args.feed_base

    (old_feed, old_vers) = get_feed_and_vers(old_branch)
    (new_feed, new_vers) = get_feed_and_vers(new_branch)

    old_core_pkgs: dict[str, 'Package'] = {}
    new_core_pkgs: dict[str, 'Package'] = {}
    old_extra_pkgs: dict[str, 'Package'] = {}
    new_extra_pkgs: dict[str, 'Package'] = {}
    for arch in SUB_FEEDS:
        old_core_pkgs |= get_packages(feed_base, old_feed, 'main', arch, old_branch)
        new_core_pkgs |= get_packages(feed_base, new_feed, 'main', arch, new_branch)
        old_extra_pkgs |= get_packages(feed_base, old_feed, 'extra', arch, old_branch)
        new_extra_pkgs |= get_packages(feed_base, new_feed, 'extra', arch, new_branch)

    report: dict = gen_report(
        old_core_pkgs, new_core_pkgs, old_extra_pkgs, new_extra_pkgs, old_vers, new_vers
    )

    print(dumps(report))

    return 0

if __name__ == '__main__':
    parser = CLIParser()
    args = parser.parse_args()
    sys.exit(main(args))

