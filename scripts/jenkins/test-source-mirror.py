#!/usr/bin/env python2
import os
import sys
import re
import urllib2

print '===== Checking source mirror ====='

# is it enabled
if os.environ['MIRROR_URL'] == '':
    print 'WARNING: This test is disabled because of empty $MIRROR_URL. Skipping.'
    sys.exit(0)

sys.stdout.flush()

# config
download_dir = os.environ['DOWNLOAD_DIR']
url = os.environ['MIRROR_URL']

pattern_re = re.compile( '<a href="(.*?)">.*?</a>' )

# get list of archives on mirror server
mirror_files = []
response = urllib2.urlopen(url)
try:
    txt = response.read()
    mirror_files = pattern_re.findall(txt)
finally:
    response.close()

# check local versus remote archive list
tarball_exts_re = re.compile( '.*\.gz$|.*\.tgz$|.*\.xz$|.*\.txz$|.*\.bz2$|.*\.tbz2$' )
ni_git_tarball_prefix_re = re.compile( '^git2_git.amer.corp.natinst.com.*' )

missing_files = 0
for f in os.listdir(download_dir):
    if tarball_exts_re.match(f) and not ni_git_tarball_prefix_re.match(f):
        if f not in mirror_files:
            print >> sys.stderr, 'ERROR: Source archives %s not found on mirror server' % f
            missing_files = missing_files + 1

if missing_files == 0:
    print 'No missing source archives on mirror server %s' % url
else:
    print >> sys.stderr, 'ERROR: %s source archives missing from mirror server %s. Please upload these files to the server.' % (missing_files, url)
    sys.exit(1)
