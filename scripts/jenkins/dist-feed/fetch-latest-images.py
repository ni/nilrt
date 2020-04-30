#!/usr/bin/env python3
import sys
if sys.version_info[0] < 3 or sys.version_info[1] < 5:
    print('Script ' + __file__ + ' requires python>=3.5.')
    sys.exit(1)

import jinja2 as j2
import os
import shutil
import subprocess as sp
import sys
import tempfile
import threading
import yaml
import zipfile  # for handling zipped nibuild exports
from tempfile import mkdtemp
from time import sleep
from datetime import datetime, timedelta
from queue import Queue

# PATH Fixing and dynamic linking #
import niversion
from niversion import NiBuildVersion
import ni_mounts

OPKG_UTILS_PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), 'opkg-utils'))
# add opkg-utils to library search path
sys.path.insert(0, OPKG_UTILS_PATH)
import opkg
#####

from pprint import pprint

# LOGGING #
import logging
logging.basicConfig(format='[%(threadName)-10s] %(message)s')


class FetcherException(Exception):
    pass


class ManifestException(Exception):
    pass


class NILRTDistFetcher():
    """Fetches IPK entries from disk into feed.

    This class is designed to work with entries taken from the
    NILRTDistFeedManifest class and to construct the NILRT dist/ feed.
    """

    def __init__(self, retain_temp=False, staging_dir=None):
        """Initialize the NILRTDistFetcher object.

        A NILRTDistFetcher instance owns a temporary directory, in which it
        does its work.

        Args:
            retain_temp: If True, do not delete the temporary (staging)
                directory, when this object is garbage collected.
            staging_dir: (PathLike) path into which this object should perform
                its staging. It will be created if it does not already exist.
                If None, use a random temporary directory (provided by the OS).
        """
        self.retain_temp = retain_temp

        # setup staging tempdir
        if staging_dir is None:
            self.staging = mkdtemp()
        else:
            self.staging = staging_dir

        logging.debug('Using staging directory: %s' % self.staging)
        # reset the work directory
        self._create_clean_dir(self.__p_staging_work())
        # reset the staging feed directory
        self._create_clean_dir(self.__p_staging_feed())

        self.rich_env = os.environ
        self.rich_env['PATH'] = ':'.join([os.environ['PATH'], OPKG_UTILS_PATH])
        logging.debug('Using rich PATH=%s' % self.rich_env['PATH'])

    def __del__(self):
        """Delete this NILRTDistFetcher instance.

        If the value of self.retain_temp is True, the staging directory will
        not be deleted. Otherwise, it will be removed.
        """
        if self.retain_temp:
            print('Retain Temp asserted. Not cleaning staging directory:\n%s' % self.staging)
        else:
            # it is not save to assume that globals still exist in a __del__
            if logging is not None:
                logging.debug('Cleaning staging directory: %s' % self.staging)
            shutil.rmtree(self.staging)

    def __p_staging(self, *args):
        """Generate a path, whose root is the staging directory."""
        return os.path.join(self.staging, *args)

    def __p_staging_feed(self, *args):
        """Generate a path, whose root is the staging feed directory."""
        return self.__p_staging('feed', *args)

    def __p_staging_work(self, *args):
        """Generate a path, whose root is the staging work directory."""
        return self.__p_staging('work', *args)

    def _create_clean_dir(self, path):
        """Create a clean directory at "path".

        Args:
            path: (PathLike) destination to create and/or clean.
        """
        try:
            shutil.rmtree(path)
        except FileNotFoundError: pass
        try:
            os.mkdir(path)
        except FileNotFoundError: pass

    def create_package_index(self):
        """Generate package index files for the staging feed.

        Use the opkg-utils scripts to create an opkg-compliant Packages file
        for all IPKs in the staging feed, including checksum information for
        each.

        Raises:
            subprocess.CalledProcessError: if raised by the ``opkg-make-index``
                script.
        """

        logging.info('Creating package index files...')
        os.chdir(self.__p_staging_feed())
        try:
            proc = sp.run(['opkg-make-index',
                           '--checksum', 'md5', '--checksum', 'sha256',
                           '-p', 'Packages', '-v', '-f', '-a',
                           self.__p_staging_feed()],
                           env=self.rich_env,
                           stdout=sp.PIPE, stderr=sp.PIPE,
                           universal_newlines=True, check=True)
        except sp.CalledProcessError as e:
            logging.error(e.stdout)
            logging.error(e.stderr)
            raise e
        else:
            logging.debug(proc.stdout)
            logging.debug(proc.stderr)

    def _check_sum_ipk(self, ipk_path, packages_file):

        def __try_compare_checksum(real_ipk, ref_ipk, algorithm):
            try:
                return getattr(real_ipk, algorithm) == getattr(ref_ipk, algorithm)
            except KeyError: return None

        # read the packages_file into an opkg.Packages collection
        index_packages = opkg.Packages()
        index_packages.read_packages_file(packages_file)

        filename = os.path.basename(ipk_path)
        for pkg, info in index_packages.packages.items():
            # match the index info paragraph by filename
            if info.filename == filename:
                real_ipk = opkg.Package(ipk_path)
                sums = [
                    __try_compare_checksum(real_ipk, info, 'md5'),
                    __try_compare_checksum(real_ipk, info, 'sha256'),
                    __try_compare_checksum(real_ipk, info, 'size'),
                ]
                # raise iff all checksum methods report that there is no info
                if all([checksum is None for checksum in sums]):
                    raise FetcherException('No checksum information for ipk paragraph.')
                else:
                    # return True, iff all declared checksums pass; else,
                    # return False
                    return all([checksum for checksum in sums if checksum is not None])
        # only get here if no packages match by filename
        raise FetcherException('No package in index matches: %s' % filename)

    def check_ipk_complete(self, ipk_path):
        """Validates that the IPK at ipk_path is a "complete" file.

        If an IPK is fetched from a remote source (like a file server, it is
        possible that the file is still being written when the fetcher attempts
        to read it. Therefore, we need to compare the checksum of the IPK
        against information provided by an opkg package index file, to validate
        that the file is "complete" before copying.

        Args:
            ipk_path: (PathLike) path to the source IPK. Packages files will be
                sourced from the same directory.

        Returns:
            True, if the IPK passed validation; False otherwise.

        Raises:
            FetcherException: if the IPK export contains no Packages file

        """

        export_dir = os.path.dirname(ipk_path)

        # try to find a Packages file in the export directory
        if any([f == 'Packages' for f in os.listdir(export_dir)]):
            try:
                return self._check_sum_ipk(ipk_path, os.path.join(export_dir, 'Packages'))
            except FetcherException as e:
                raise e  # we don't handle any case other than Packages files atm
        else:
            raise FetcherException('No Packages file found in export location: \'%s\'. Cannot checksum IPK.' % export_dir)

    def fetch_dist_ipk(self, ipk_name, ipk_path, job_queue,
                       symlink=False, retry=(15, 60)):
        """Fetch and validte an IPK from the disk.

        Fetches (copy or symlink) an IPK from ipk_path to the staging work
        directory. Validates that IPK against any Packages index files found in
        the source location. If it passes validation, copy the IPK to the
        staging feed.

        Fetch status is communicated through the job_queue parameter object. If
        the fetch succeeds and the IPK passes validation, the path to the IPK
        (in the staging feed) is inserted to the Queue. Otherwise, a
        FetcherException is inserted, with information about why the fetch
        failed.

        Args:
            ipk_name: (str) nice name of the manifest entry
            ipk_path: (PathLike) source path for the IPK; Package files will be
                searched in the same directory.
            job_queue: queue.Queue object, into which the return values
                will be placed.
            symlink: If True, create the feed using symlinks to the manifest
                IPKs; else, copy the IPKs.
            retry: (tuple) of (retry_inerval, timeout), specifying how
                frequently the fetcher should try to re-fetch the source file,
                if it fails validation.

        Returns:
            None; other than the job_queue entry
        """

        logging.info('Fetching: %s' % ipk_name)

        # Check that the source file is "complete" ie. entirely mirrored on the
        # file server.
        validated = False
        time_now = datetime.now()
        time_timeout = time_now + timedelta(seconds=retry[1])
        while not validated:
            time_now = datetime.now()
            try:
                validated = self.check_ipk_complete(ipk_path)
            except FetcherException as e:
                # handle the case that there is no Packages file, by just
                # accepting the IPK.
                logging.warning(str(e))
                break

            if validated:
                break
            if not validated:
                logging.warning('IPK %s failed validation @ %s.' % (ipk_name,
                    time_now.isoformat()))
                if time_timeout > time_now:
                    sleep(retry[0])  # sleep for the retry interval
                else:
                    job_queue.put((ipk_name, FetcherException('IPK \'%s\' timed out after failing to validate.' % ipk_name)))
                    return None

        # Copy (or symlink to) the mirrored file in the staging feed
        feed_ipk = self.__p_staging_feed(os.path.basename(ipk_path))
        if symlink:
            os.symlink(ipk_path, feed_ipk)
            logging.debug('Symlinked IPK to: %s' % feed_ipk)
        else:
            shutil.copy(ipk_path, feed_ipk)
            logging.debug('Copied IPK to: %s' % feed_ipk)
        job_queue.put((ipk_name, feed_ipk))
        return None

    def fetch_dist_ipks(self, manifest, output_dir=None, symlink=False):
        """Fetches all package entries in the given manifest.

        Iterates through the manifest object and copies each dist entry to the
        staging directory, validates the IPKs, then creates a package index,
        and (optionally) deposits the feed in the output_dir location.

        Args:
            manifest: NILRTDistFetcherManifest object of packages to fetch
            output_dir: PathLike to where the resulting feed manifest should be
                deposited. Directory will be created, if it does not exist. If
                None, do not deposit the feed anywhere (leave it in the temp
                directory.)
            symlink: If True, create the feed using symlinks to the manifest
                IPKs; else, copy the IPKs.
        """

        if output_dir is not None:
            output_dir = os.path.realpath(output_dir)

        # fetch and process IPKs in threads
        threads = []
        # Queue objects can have two values:
        #   1. a Path-like object to the validated IPK file, in the staging feed
        #   2. a FetcherException object, with an error message
        # See the fetch_dist_ipk method for more info
        job_queue = Queue()

        for package in manifest.packages():
            thread = threading.Thread(target=self.fetch_dist_ipk,
                                      name='fetcher_' + package.name,
                                      args=(package.name, package.ipk, job_queue),
                                      kwargs={'symlink': symlink})
            threads.append(thread)
            thread.start()

        # wait for fetches to complete before continuing
        [thread.join() for thread in threads]
        # the staging feed should now be populated with the validated IPKs

        # Evaluate the job results. Fail out if any of the jobs failed.
        job_results = []
        while not job_queue.empty():
            job_results.append(job_queue.get())

        for job, result in job_results:
            if isinstance(result, FetcherException):
                logging.critical('%s = %s' % (job, str(result)))
            else:
                logging.info('%s = %s' % (job, str(result)))
        if any([isinstance(result, FetcherException) for job, result in job_results]):
            raise FetcherException('Some fetch jobs failed.')

        self.create_package_index()  # create the feed index

        # (optionally) copy the temp feed to an output location
        if output_dir is not None:
            logging.info('Copying feed objects to: %s' % output_dir)
            os.makedirs(output_dir, exist_ok=True)
            feed_files = os.listdir(self.__p_staging_feed())
            # use the cp utility to copy feed objects because python's
            # shutils copy methods are janky.
            try:
                proc = sp.run(['cp', '-vrfP'] + feed_files + [output_dir],
                              stdout=sp.PIPE, stderr=sp.PIPE,
                              universal_newlines=True, check=True)
            except sp.CalledProcessError as e:
                logging.error(e.stdout)
                logging.error(e.stderr)
                raise e
            else:
                logging.debug(proc.stdout)


class NILRTDistFetcherManifest():

    class PackageEntry():

        def __init__(self, package_name, configs, j2_env):
            self.name = str(package_name)
            self.raw  = configs
            if not isinstance(configs, dict):
                raise ValueError('Package entry "%s" has invalid config values. Expected dict, got %s' % (package_name, type(configs)))
            # parse config values
            self.export = j2_env.from_string(self.raw['export']).render()
            self._find_ipk_path(self.export, self.raw['ipk_path'])
            self.final_only = bool(configs.get('final_only', False))

        def _find_ipk_path(self, export_root, ipk_path):
            """Finds an IPK using the  ``ipk_path`` and ``export_root``.

            Uses the ``ipk_path`` and ``export_root`` to build search
            parameters for the ``find`` utility to search for IPKs. Returns the
            full path to a single IPK result.

            Args:
                export_root: PathLike to the root of the search domain.
                ipk_path: wildcard str to be passed to the find utility's
                    ``-path`` parameter.
            Returns:
                PathLike to the single IPK search result.
            Throws:
                ManifestException if multiple IPKs match the search string OR
                    if no IPKs match the search string.
            """
            if not ipk_path.startswith(export_root):
                ipk_path = '/'.join([export_root, ipk_path])
            self.ipk = None

            # use the 'find' utility to locate IPKs by wildcard path
            proc = sp.run(['find', export_root, '-path', ipk_path],
                          stdout=sp.PIPE, stderr=sp.PIPE,
                          universal_newlines=True, check=True,
                          timeout=30)
            logging.debug(str(proc))

            hits = proc.stdout.splitlines()
            for i in range(0, len(hits)):
                logging.debug('[match %d] %s' % (i+1, hits[i]))

            if len(hits) > 1:
                raise ManifestException('Multiple files match IPK path: "%s"; you must disambiguate the path.' % ipk_path)

            try:
                self.ipk = hits[0]
            except IndexError:
                raise ManifestException('No IPK found matching path: %s' % ipk_path)


    def __init__(self, manifest_path):
        """Initializes the NILRTDistFetcherManifest instance.

        Args:
            manifest_path: (PathLike) to the manifest file, which is to be
                parsed.
        """
        with open(manifest_path, 'r') as fp_manifest:
            self.manifest_data = yaml.safe_load(fp_manifest)

        # init jinja2 Environment
        self.env = j2.Environment()
        self.__init_j2_globals()
        self.__init_j2_filters()
        self._temp_assets = []

    def __init_j2_globals(self):
        """Jinja2 template global variables (for use in manifest files.)"""
        ni_network_mounts = {
            'MNT_BALTIC_PENGUINEXPORTS': ni_mounts.locate_network_mount_penguinExports(),
            'MNT_NIRVANA_PERFORCEEXPORTS': ni_mounts.locate_network_mount_perforceExports(),
        }
        self.env.globals.update(ni_network_mounts)

    def __init_j2_filters(self):
        """Jinja2 template filters (for use in manifest files.)"""
        self.env.filters['latest_export'] = self.filter_latest_export
        self.env.filters['unzip'] = self.filter_unzip

    def __del__(self):
        for asset in self._temp_assets:
            asset.cleanup()

    def filter_latest_export(self, export_path, final_only=False):
        """Jinja2 Filter: returns the latest NIBuild export from input path.

        Searches the directory at export_path for subdirectories following the
        NIBuild version scheme. Uses the *latest* version to build a full path
        and returns it.

        Files/Directories which cannot be interpreted as an NIBuild Version are
        ignored.

        Args:
            export_path: PathLike to the export location

        Returns:
            PathLike full path to the latest export.
        """
        final_enum = niversion.Phase.from_letter('f')

        versions = []
        for f in os.listdir(export_path):
            if not os.path.isdir(os.path.join(export_path, f)):
                continue  # ignore non-directories
            export_version = NiBuildVersion.try_parse(f)
            if export_version is None:
                continue  # ignore non-NI Version dirs
            if final_only and export_version.phase != final_enum:
                continue  # ignore non-final, iff final_only asserted
            versions.append(export_version)
        # versions now contains only valid export directories
        if len(versions) == 0:
            raise ValueError('No NIBuild versions found at location: %s, or no non-final versions with final_only asserted.' % export_path)
        else:
            latest_version = sorted(versions, reverse=True)[0]
            return os.path.join(export_path, str(latest_version))

    def filter_unzip(self, zip_path, zip_password=None):
        if not zipfile.is_zipfile(zip_path):
            raise ManifestException('Path \'%s\' is not a zip file.' % zip_path)

        with zipfile.ZipFile(zip_path, mode='r') as zip_file:
            zip_dir = tempfile.TemporaryDirectory()
            # add the temp_dir to the assets list so that it will be deleted by
            # garbage collection when the Manifest object falls from scope
            self._temp_assets.append(zip_dir)
            zip_file.extractall(path=zip_dir.name, pwd=zip_password)
        # return the temp dir (with unzipped contents) as the new path
        return zip_dir.name

    def packages(self):
        """Iterates through each package entry in the manifest.

        Returns:
            Iterator of NILRTDistFetcherManifest.PackageEntry objects.
        """
        for package, configs in self.manifest_data['packages'].items():
            if configs is None:
                logging.error("Package entry %s has no data or bad syntax." % package)
            yield self.PackageEntry(package, configs, self.env)



# CLI #
#######


if __name__ == "__main__":
    # CLI arguments
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-r', '--retain-temp', action='store_true',
                        help='Do not delete the temporary staging directory.')
    parser.add_argument('-s', '--symlink', action='store_true')
    parser.add_argument('output_directory')
    parser.add_argument('manifest_file', nargs='?', default='dist-feed-manifest.yml')

    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug(args)


    # load the manfiest file
    logging.info('Using manifest file: %s' % args.manifest_file)
    manifest = NILRTDistFetcherManifest(args.manifest_file)
    # fetch and sign manifest entries
    fetcher = NILRTDistFetcher(retain_temp=args.retain_temp)
    fetcher.fetch_dist_ipks(manifest, args.output_directory, symlink=args.symlink)
    # Explicitly destroy the fetcher to increase the liklihood that the logger
    # is still around.
    del fetcher

    sys.exit(0)
