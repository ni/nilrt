#
# Copyright (c) 2026 Emerson Electric Co.
#
# SPDX-License-Identifier: MIT
#
"""is a manually run regression suite for the new feed-SBOM integration.
NI packages installed from feeds don’t have recipes, so OpenEmbedded can’t generate their SPDX inventory from the build;
the PR fetches their CycloneDX SBOMs and converts them into the image’s SPDX document.

The tests use a fake feed and temporary cache, so they check URL lookup, package identity/MD5 validation,
caching and offline behavior, and CycloneDX-to-SPDX conversion without relying on the live package server or a full image build.
It’s marked manual because it’s a standalone unittest script, not part of the regular automated test runner.
OpenEmbedded source checkouts:
To test against a specific OpenEmbedded-Core checkout, set OECORE_SRC:
    OECORE_SRC=/path/to/openembedded-core python3 -B scripts/tests/test_feed_sbom.py
"""
#
import io
import json
import os
import sys
import tempfile
import urllib.parse
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
NILRT_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SOURCES = os.path.join(NILRT_ROOT, "sources")
META_NILRT_LIB = os.path.join(SOURCES, "meta-nilrt-pr1134", "lib")
OECORE_SRC = os.environ.get("OECORE_SRC", os.path.join(SOURCES, "openembedded-core"))
OE_LIB = os.path.join(OECORE_SRC, "meta", "lib")
BITBAKE_LIB = os.path.join(SOURCES, "bitbake", "lib")
sys.path[:0] = [META_NILRT_LIB, OE_LIB, BITBAKE_LIB]

import bb.data  # noqa: E402
import oe.sbom30  # noqa: E402
import oe.spdx30  # noqa: E402
from nilrt import feed_sbom  # noqa: E402

POOL = "http://pool.example/ni/linuxpkg/pool/ipk"
NAME, VER, ARCH = "ni-sysapi", "27.0.0.60-0+d60", "core2-64"
MD5 = "b5063f83be75eb9d04be3a5e5c6f673c"
VDIR = POOL + "/ni-s/ni-sysapi/27.0.0/27.0.0.60-0%2Bd60/"
SBOM_URL = VDIR + "8a10e89c/ni-sysapi_27.0.0.60-0%2Bd60_core2-64.ipk.cdx.sbom.json"


def listing(*hrefs):
    links = "".join('<A HREF="%s">%s</A><br>' % (h, h.rstrip("/").split("/")[-1]) for h in hrefs)
    return ('<html><body><A HREF="/ni/linuxpkg/pool/">[To Parent Directory]</A><br>%s</body></html>' % links).encode()


def sample_cdx(name=NAME, version=VER, arch=ARCH, md5=MD5):
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": "urn:uuid:f3d01351-29e0-47fa-8c37-4df86d0531a2",
        "metadata": {
            "component": {
                "type": "library",
                "name": name,
                "version": version,
                "purl": "pkg:generic/ipk/%s@%s?architecture=%s" % (name, version.replace("+", "%2B"), arch),
                "supplier": {"name": "NI"},
                "copyright": "National Instruments, Inc. All rights reserved.",
                "hashes": [{"alg": "MD5", "content": md5}],
                "licenses": [{"license": {"name": "National Instruments, Inc.",
                                          "url": "https://www.ni.com/en/about-ni/legal/software-license-agreement.html"}}],
            },
        },
        "components": [
            {"type": "library", "name": "CPUInfo", "version": "16.0.0f1", "supplier": {"name": "NI"},
             "licenses": [{"license": {"name": "National Instruments, Inc."}}]},
            {"type": "library", "name": "LVRTEthernet", "version": "2.0.0b3"},
            {"type": "library", "name": "LVRTEthernet", "version": "2.0.0f0"},
            {"type": "library", "name": "zlib", "version": "1.3.1", "purl": "pkg:generic/zlib@1.3.1",
             "cpe": "cpe:2.3:a:zlib:zlib:1.3.1:*:*:*:*:*:*:*",
             "licenses": [{"license": {"id": "Zlib"}}],
             "hashes": [{"alg": "SHA-256", "content": "AB" * 32}]},
            {"type": "library", "name": "openssl", "version": "3.0.13",
             "licenses": [{"expression": "Apache-2.0 OR MIT"}]},
        ],
    }


class FakePool:
    """Serves the pool layout seen on argohttp: one version folder with one
    build-hash folder per architecture."""

    def __init__(self, cdx=None):
        self.files = {
            POOL + "/": listing("/ni/linuxpkg/pool/ipk/ni-s/", "/ni/linuxpkg/pool/ipk/nirt/"),
            VDIR: listing("/ni/linuxpkg/pool/ipk/ni-s/ni-sysapi/27.0.0/27.0.0.60-0%2Bd60/59205b1e/",
                          "/ni/linuxpkg/pool/ipk/ni-s/ni-sysapi/27.0.0/27.0.0.60-0%2Bd60/8a10e89c/"),
            SBOM_URL: json.dumps(cdx or sample_cdx()).encode(),
        }
        self.requests = []

    def get(self, url):
        self.requests.append(url)
        return self.files.get(url)


class PathTests(unittest.TestCase):
    def test_version_series(self):
        self.assertEqual(feed_sbom.version_series("27.0.0.60-0+d60"), "27.0.0")
        self.assertEqual(feed_sbom.version_series("26.3.0.49300-0+f148"), "26.3.0")
        self.assertEqual(feed_sbom.version_series("1:20.0.0.49152-0+f0"), "20.0.0")
        with self.assertRaises(feed_sbom.FeedSbomError):
            feed_sbom.version_series("git-r0")

    def test_version_dir_url_quotes_plus(self):
        self.assertEqual(feed_sbom.version_dir_url(POOL, "ni-s", NAME, VER), VDIR)

    def test_list_subdirs_ignores_parent_and_other_paths(self):
        html = listing("/ni/linuxpkg/pool/ipk/ni-s/ni-sysapi/27.0.0/27.0.0.60-0%2Bd60/8a10e89c/").decode()
        self.assertEqual(feed_sbom.list_subdirs(html, VDIR), ["8a10e89c"])
        self.assertEqual(feed_sbom.list_subdirs(html, POOL + "/other/"), [])


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = os.path.join(self.tmp.name, "cache")

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_matching_arch_in_build_hash_folders(self):
        pool = FakePool()
        self.assertEqual(feed_sbom.find_sbom_url(POOL, NAME, VER, ARCH, get=pool.get), SBOM_URL)

    def test_http_get_checks_redirect_target_before_following(self):
        checked = []

        def check_url(url):
            checked.append(url)
            if urllib.parse.urlsplit(url).hostname != "pool.example":
                raise feed_sbom.FeedSbomError("redirect target is not allowed")

        class RedirectingOpener:
            def __init__(self, handler):
                self.handler = handler

            def open(self, url, timeout=None):
                self.handler.redirect_request(
                    feed_sbom.urllib.request.Request(url), None, 302, "Found", {},
                    "https://untrusted.example/sbom.json")

        with patch("urllib.request.build_opener",
                   side_effect=lambda handler: RedirectingOpener(handler)):
            with self.assertRaisesRegex(feed_sbom.FeedSbomError, "not allowed"):
                feed_sbom.http_get(
                    "https://pool.example/sbom.json", retries=1, check_url=check_url)

        self.assertEqual(checked, [
            "https://pool.example/sbom.json", "https://untrusted.example/sbom.json"])

    def test_fetch_downloads_then_uses_cache(self):
        pool = FakePool()
        path, url = feed_sbom.fetch_sbom(POOL, self.cache, NAME, VER, ARCH, get=pool.get)
        self.assertEqual(url, SBOM_URL)
        with open(path) as f:
            self.assertEqual(json.load(f)["metadata"]["component"]["name"], NAME)
        offline = FakePool()
        path2, url2 = feed_sbom.fetch_sbom(POOL, self.cache, NAME, VER, ARCH, allow_network=False, get=offline.get)
        self.assertEqual((path2, url2), (path, SBOM_URL))
        self.assertEqual(offline.requests, [])

    def test_selects_later_build_matching_feed_md5(self):
        pool = FakePool()
        first_url = SBOM_URL.replace("8a10e89c", "59205b1e")
        pool.files[first_url] = json.dumps(sample_cdx(md5="0" * 32)).encode()
        path, url = feed_sbom.fetch_sbom(
            POOL, self.cache, NAME, VER, ARCH, md5=MD5, get=pool.get)
        self.assertEqual(url, SBOM_URL)
        self.assertIn(first_url, pool.requests)
        self.assertEqual(pool.requests.count(SBOM_URL), 1)
        with open(path) as f:
            self.assertEqual(feed_sbom.verify_sbom(json.load(f), NAME, VER, ARCH, MD5), [])

    def test_malformed_candidate_does_not_abort_search(self):
        for index, metadata in enumerate(([], {"component": []})):
            with self.subTest(metadata=metadata):
                pool = FakePool()
                first_url = SBOM_URL.replace("8a10e89c", "59205b1e")
                pool.files[first_url] = json.dumps({
                    "bomFormat": "CycloneDX", "metadata": metadata,
                }).encode()
                path, url = feed_sbom.fetch_sbom(
                    POOL, os.path.join(self.cache, str(index)), NAME, VER, ARCH,
                    md5=MD5, get=pool.get)
                self.assertEqual(url, SBOM_URL)
                with open(path) as f:
                    self.assertEqual(feed_sbom.verify_sbom(
                        json.load(f), NAME, VER, ARCH, MD5), [])

    def test_feed_md5_changes_use_independent_cache_paths(self):
        pool = FakePool()
        path, _ = feed_sbom.fetch_sbom(
            POOL, self.cache, NAME, VER, ARCH, md5=MD5, get=pool.get)
        replacement_md5 = "1" * 32
        pool.files[SBOM_URL] = json.dumps(sample_cdx(md5=replacement_md5)).encode()
        path2, _ = feed_sbom.fetch_sbom(
            POOL, self.cache, NAME, VER, ARCH, md5=replacement_md5, get=pool.get)
        self.assertNotEqual(path2, path)
        with open(path) as f:
            self.assertEqual(feed_sbom.verify_sbom(json.load(f), NAME, VER, ARCH, MD5), [])
        with open(path2) as f:
            self.assertEqual(feed_sbom.verify_sbom(
                json.load(f), NAME, VER, ARCH, replacement_md5), [])
        self.assertEqual(feed_sbom.fetch_sbom(
            POOL, self.cache, NAME, VER, ARCH, allow_network=False, md5=MD5), (path, SBOM_URL))
        self.assertEqual(feed_sbom.fetch_sbom(
            POOL, self.cache, NAME, VER, ARCH, allow_network=False, md5=replacement_md5),
            (path2, SBOM_URL))

    def test_legacy_flat_cache_is_verified_and_migrated_offline(self):
        pool = FakePool()
        legacy, source = feed_sbom.fetch_sbom(
            POOL, self.cache, NAME, VER, ARCH, get=pool.get)
        path, migrated_source = feed_sbom.fetch_sbom(
            POOL, self.cache, NAME, VER, ARCH, md5=MD5, allow_network=False)
        self.assertNotEqual(path, legacy)
        self.assertEqual(migrated_source, source)
        self.assertEqual(os.path.dirname(path), os.path.join(self.cache, MD5))
        self.assertTrue(os.path.exists(path))
        self.assertFalse(os.path.exists(legacy))
        self.assertFalse(os.path.exists(legacy + ".url"))

    def test_parallel_feed_builds_do_not_replace_each_other(self):
        ready = Barrier(2)
        digests = (MD5, "1" * 32)

        def fetch(digest):
            pool = FakePool(sample_cdx(md5=digest))

            def get(url):
                if url == SBOM_URL:
                    ready.wait(timeout=10)
                return pool.get(url)

            return feed_sbom.fetch_sbom(
                POOL, self.cache, NAME, VER, ARCH, md5=digest, get=get)[0]

        with ThreadPoolExecutor(max_workers=2) as executor:
            paths = list(executor.map(fetch, digests))
        self.assertNotEqual(*paths)
        for path, digest in zip(paths, digests):
            with open(path) as stream:
                self.assertEqual(feed_sbom.verify_sbom(
                    json.load(stream), NAME, VER, ARCH, digest), [])

    def test_invalid_md5_cannot_form_cache_path(self):
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "Invalid feed IPK MD5"):
            feed_sbom.sbom_cache_path(self.cache, NAME, VER, ARCH, "../invalid")

    def test_matching_cache_is_verified_and_used_offline(self):
        pool = FakePool()
        expected = feed_sbom.fetch_sbom(
            POOL, self.cache, NAME, VER, ARCH, md5=MD5, get=pool.get)
        pool.requests.clear()
        self.assertEqual(feed_sbom.fetch_sbom(
            POOL, self.cache, NAME, VER, ARCH, allow_network=False,
            md5=MD5, get=pool.get), expected)
        self.assertEqual(pool.requests, [])

    def test_mismatched_cache_fails_offline_without_network(self):
        pool = FakePool()
        feed_sbom.fetch_sbom(POOL, self.cache, NAME, VER, ARCH, get=pool.get)
        pool.requests.clear()
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "MD5.*BB_NO_NETWORK"):
            feed_sbom.fetch_sbom(
                POOL, self.cache, NAME, VER, ARCH, allow_network=False,
                md5="1" * 32, get=pool.get)
        self.assertEqual(pool.requests, [])

    def test_no_matching_build_is_not_cached(self):
        pool = FakePool()
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "Rejected candidates:"):
            feed_sbom.fetch_sbom(
                POOL, self.cache, NAME, VER, ARCH, md5="1" * 32, get=pool.get)
        self.assertFalse(os.path.exists(self.cache))

    def test_offline_without_cache_fails(self):
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "BB_NO_NETWORK"):
            feed_sbom.fetch_sbom(POOL, self.cache, NAME, VER, ARCH, allow_network=False, get=FakePool().get)

    def test_missing_version_fails(self):
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "No ni-sysapi_27.0.0.99"):
            feed_sbom.fetch_sbom(POOL, self.cache, NAME, "27.0.0.99-0+d99", ARCH, get=FakePool().get)

    def test_invalid_json_is_rejected_and_not_cached(self):
        pool = FakePool()
        pool.files[SBOM_URL] = b"<html>error</html>"
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "not valid JSON"):
            feed_sbom.fetch_sbom(POOL, self.cache, NAME, VER, ARCH, get=pool.get)
        self.assertFalse(os.path.exists(os.path.join(self.cache, feed_sbom.sbom_filename(NAME, VER, ARCH))))


class VerifyTests(unittest.TestCase):
    def test_matching_sbom(self):
        self.assertEqual(feed_sbom.verify_sbom(sample_cdx(), NAME, VER, ARCH, MD5.upper()), [])

    def test_mismatches_are_reported(self):
        problems = feed_sbom.verify_sbom(sample_cdx(version="27.0.0.80-0+d80", arch="cortexa9-vfpv3"),
                                         NAME, VER, ARCH, "0" * 32)
        self.assertEqual(len(problems), 4, problems)
        self.assertTrue(any("version" in p for p in problems))
        self.assertTrue(any("purl version" in p for p in problems))
        self.assertTrue(any("architecture" in p for p in problems))
        self.assertTrue(any("MD5" in p for p in problems))

    def test_missing_arch_or_md5_evidence_is_rejected(self):
        cdx = sample_cdx()
        comp = cdx["metadata"]["component"]
        comp["purl"] = "pkg:generic/ipk/%s@%s" % (NAME, VER)
        del comp["hashes"]
        problems = feed_sbom.verify_sbom(cdx, NAME, VER, ARCH, MD5)
        self.assertEqual(len(problems), 2, problems)
        # without a feed MD5 there is nothing to compare, so only the arch fails
        self.assertEqual(len(feed_sbom.verify_sbom(cdx, NAME, VER, ARCH)), 1)

    def test_root_purl_must_match_installed_package(self):
        invalid_purls = (
            ("not-a-purl?architecture=" + ARCH, "not a valid IPK package URL"),
            ("pkg:generic/ipk/other@%s?architecture=%s" % (VER, ARCH), "purl name"),
            ("pkg:generic/ipk/%s@27.0.0.80-0%%2Bd80?architecture=%s" % (NAME, ARCH),
             "purl version"),
        )
        for purl, message in invalid_purls:
            with self.subTest(purl=purl):
                cdx = sample_cdx()
                cdx["metadata"]["component"]["purl"] = purl
                problems = feed_sbom.verify_sbom(cdx, NAME, VER, ARCH, MD5)
                self.assertTrue(any(message in problem for problem in problems), problems)

    def test_parse_opkg_lists(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "NI-main-software"), "w") as f:
                f.write("Package: ni-sysapi\nVersion: %s\nArchitecture: %s\nDescription: x\n continued: line\n"
                        "MD5Sum: %s\n\nPackage: other\nVersion: 1\nArchitecture: all\n" % (VER, ARCH, MD5.upper()))
            with open(os.path.join(d, "NIOE-all"), "w") as f:
                f.write("Package: local-package\nVersion: 1\nArchitecture: all\nMD5Sum: %s\n" % MD5)
            self.assertEqual(feed_sbom.parse_opkg_lists(d), {
                (NAME, VER, ARCH): MD5,
                ("local-package", "1", "all"): MD5,
            })
            self.assertEqual(feed_sbom.parse_opkg_lists(
                d, feed_names=("NI-main-software",)), {(NAME, VER, ARCH): MD5})
        self.assertEqual(feed_sbom.parse_opkg_lists("/does/not/exist"), {})

    def test_conflicting_feed_builds_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            for index in range(2):
                with open(os.path.join(directory, str(index)), "w") as stream:
                    stream.write("Package: %s\nVersion: %s\nArchitecture: %s\nMD5Sum: %s\n" % (
                        NAME, VER, ARCH, str(index) * 32))
            with self.assertRaisesRegex(feed_sbom.FeedSbomError, "Conflicting"):
                feed_sbom.parse_opkg_lists(directory)


class ConvertTests(unittest.TestCase):
    def setUp(self):
        self.d = bb.data.init()
        for key, value in {
            "PN": "test-image", "BB_UNIHASH": "abcdef", "SPDX_UUID_NAMESPACE": "openembedded.org",
            "SPDX_NAMESPACE_PREFIX": "https://spdx.example", "SPDX_TOOL_NAME": "test",
            "SPDX_TOOL_VERSION": "1", "SPDX_AUTHORS": "", "SPDX_VERSION": "3.0.1",
            "SPDX_EXTERNAL_PACKAGE_FUNC": "",
        }.items():
            self.d.setVar(key, value)
        self.objset = oe.sbom30.ObjectSet.new_objset(self.d, "test", copy_from_bitbake_doc=False)
        author = self.objset.add(oe.spdx30.Organization(
            _id="https://spdx.example/author", name="Test author",
            creationInfo=self.objset.doc.creationInfo))
        self.objset.doc.creationInfo.createdBy.append(author)
        self.objset.doc.profileConformance = [oe.spdx30.ProfileIdentifierType.core]
        self.license_data = {
            "licenses": {name: {} for name in ("Zlib", "MIT", "Apache-2.0")},
            "licenseListVersion": "3.24",
        }

    def convert(self, cdx=None):
        return feed_sbom.cyclonedx_to_spdx30(
            self.objset, cdx or sample_cdx(), NAME, VER, ARCH,
            self.license_data, source_url=SBOM_URL)

    def serialize(self):
        buf = io.BytesIO()
        self.objset.objects.add(self.objset.doc)
        oe.spdx30.JSONLDInlineSerializer().write(self.objset, buf, force_at_graph=True)
        return json.loads(buf.getvalue())

    def test_main_package(self):
        package = self.convert()
        self.assertEqual(package.name, NAME)
        self.assertEqual(package.software_packageVersion, VER)
        self.assertEqual(package.software_primaryPurpose, oe.spdx30.software_SoftwarePurpose.install)
        self.assertEqual(package.software_downloadLocation, SBOM_URL[:-len(".cdx.sbom.json")])
        self.assertEqual(package.verifiedUsing[0].hashValue, MD5)
        self.assertEqual(package.suppliedBy.name, "NI")
        self.assertIn("architecture=core2-64", package.software_packageUrl)
        self.assertIn(SBOM_URL, package.software_sourceInfo)

    def test_bom_document_license_is_not_assigned_to_main_package(self):
        for component_licenses in (None, [{"license": {"id": "MIT"}}]):
            with self.subTest(component_licenses=component_licenses):
                self.setUp()
                cdx = sample_cdx()
                cdx["metadata"]["licenses"] = [{"license": {"id": "CC0-1.0"}}]
                if component_licenses is None:
                    del cdx["metadata"]["component"]["licenses"]
                else:
                    cdx["metadata"]["component"]["licenses"] = component_licenses
                package = self.convert(cdx)
                licenses = [
                    target.simplelicensing_licenseExpression
                    for relationship in self.objset.foreach_type(oe.spdx30.Relationship)
                    if relationship.from_ == package
                    and relationship.relationshipType == oe.spdx30.RelationshipType.hasDeclaredLicense
                    for target in relationship.to
                ]
                self.assertEqual(licenses, [] if component_licenses is None else ["MIT"])
                annotations = list(self.objset.foreach_type(oe.spdx30.Annotation))
                self.assertEqual(len(annotations), 1)
                self.assertIn("BOM document licenses (not package licenses)", annotations[0].statement)
                self.assertIn("CC0-1.0", annotations[0].statement)
                self.serialize()

    def test_sha3_and_existing_hash_algorithms_serialize_correctly(self):
        cdx = sample_cdx()
        hashes = {
            "SHA3-256": ("sha3_256", 32), "SHA3-384": ("sha3_384", 48),
            "SHA3-512": ("sha3_512", 64), "SHA-1": ("sha1", 20),
            "SHA-256": ("sha256", 32), "SHA-384": ("sha384", 48),
            "SHA-512": ("sha512", 64), "MD5": ("md5", 16),
        }
        cdx["components"][0]["hashes"] = [
            {"alg": name, "content": "AB" * size} for name, (_, size) in hashes.items()
        ]
        self.convert(cdx)
        doc = self.serialize()
        component = next(obj for obj in doc["@graph"] if obj.get("name") == "CPUInfo")
        self.assertEqual(
            {entry["algorithm"]: entry["hashValue"] for entry in component["verifiedUsing"]},
            {algorithm: "ab" * size for algorithm, size in hashes.values()},
        )

    def test_identical_bom_licenses_keep_distinct_package_annotations(self):
        packages = []
        for name in (NAME, "other-package"):
            cdx = sample_cdx(name=name)
            cdx["metadata"]["licenses"] = [{"license": {"id": "CC0-1.0"}}]
            packages.append(feed_sbom.cyclonedx_to_spdx30(
                self.objset, cdx, name, VER, ARCH, self.license_data))
        annotations = list(self.objset.foreach_type(oe.spdx30.Annotation))
        self.assertEqual(len(annotations), 2)
        self.assertEqual({a.subject._id for a in annotations}, {p._id for p in packages})
        self.assertEqual(len({a._id for a in annotations}), 2)
        self.serialize()

    def test_cpe_binding_controls_identifier_type(self):
        cdx = sample_cdx()
        cdx["components"][0]["cpe"] = "cpe:/a:example:library:1.0"
        self.convert(cdx)
        doc = self.serialize()
        identifiers = {
            obj["name"]: obj["externalIdentifier"][0]
            for obj in doc["@graph"] if obj.get("type") == "software_Package"
            and obj.get("externalIdentifier")
        }
        self.assertEqual(identifiers["CPUInfo"]["externalIdentifierType"], "cpe22")
        self.assertEqual(identifiers["CPUInfo"]["identifier"], "cpe:/a:example:library:1.0")
        self.assertEqual(identifiers["zlib"]["externalIdentifierType"], "cpe23")
        cdx["components"][0]["cpe"] = "invalid"
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "Unsupported CPE binding"):
            self.convert(cdx)

    def test_components_and_licenses(self):
        self.convert()
        doc = self.serialize()
        self.assertEqual(doc["@context"], "https://spdx.org/rdf/3.0.1/spdx-context.jsonld")
        packages = list(self.objset.foreach_type(oe.spdx30.software_Package))
        self.assertEqual(len(packages), 6)
        self.assertEqual(len({p._id for p in packages}), 6)
        zlib = next(p for p in packages if p.name == "zlib")
        self.assertEqual(zlib.verifiedUsing[0].hashValue, "ab" * 32)
        self.assertEqual(zlib.externalIdentifier[0].externalIdentifierType,
                         oe.spdx30.ExternalIdentifierType.cpe23)
        expressions = list(self.objset.foreach_type(oe.spdx30.simplelicensing_LicenseExpression))
        self.assertEqual({p.simplelicensing_licenseExpression for p in expressions},
                         {"Zlib", "Apache-2.0 OR MIT"})
        main = next(p for p in packages if p.name == NAME)
        self.assertIn("National Instruments", main.comment)
        self.assertEqual(list(self.objset.foreach_type(oe.spdx30.simplelicensing_SimpleLicensingText)), [])
        parsed = oe.spdx30.SHACLObjectSet()
        oe.spdx30.JSONLDDeserializer().read(io.BytesIO(json.dumps(doc).encode()), parsed)
        self.assertEqual(len(list(parsed.foreach_type(oe.spdx30.software_Package))), 6)

    def test_nested_components_preserve_both_trees_and_parent_relationships(self):
        cdx = sample_cdx()
        cdx["components"] = [{"name": "top", "components": [{"name": "nested"}]}]
        cdx["metadata"]["component"]["components"] = [{"name": "metadata-child"}]
        self.convert(cdx)
        contains = {
            (r.from_.name, child.name)
            for r in self.objset.foreach_type(oe.spdx30.Relationship)
            if r.relationshipType == oe.spdx30.RelationshipType.contains
            for child in r.to
        }
        self.assertEqual(contains, {(NAME, "top"), ("top", "nested"), (NAME, "metadata-child")})

    def test_unnamed_nested_component_fails_instead_of_disappearing(self):
        cdx = sample_cdx()
        cdx["metadata"]["component"]["components"] = [
            {"name": "parent", "components": [{"version": "1"}]}]
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "under parent has no name"):
            self.convert(cdx)

    def test_unknown_license_is_preserved_without_inventing_full_text(self):
        entries = (
            {"license": {"id": "NotAnSpdxId"}},
            {"expression": "NotAnSpdxId"},
            {"expression": "MIT OR ("},
        )
        for entry in entries:
            with self.subTest(entry=entry):
                self.setUp()
                cdx = sample_cdx()
                cdx["components"] = [{"name": "x", "version": "1", "licenses": [entry]}]
                self.convert(cdx)
                package = next(p for p in self.objset.foreach_type(
                    oe.spdx30.software_Package) if p.name == "x")
                self.assertIn("NotAnSpdxId" if "NotAnSpdxId" in str(entry) else "MIT OR (",
                              package.comment)
                self.assertEqual(list(self.objset.foreach_type(
                    oe.spdx30.simplelicensing_LicenseExpression)), [])
                self.serialize()

    def test_known_spdx_license_exception_expression_is_preserved(self):
        self.license_data["exceptions"] = [{"licenseExceptionId": "LLVM-exception"}]
        cdx = sample_cdx()
        cdx["components"] = [{"name": "x", "licenses": [
            {"expression": "Apache-2.0 WITH LLVM-exception"}]}]
        self.convert(cdx)
        expressions = list(self.objset.foreach_type(oe.spdx30.simplelicensing_LicenseExpression))
        self.assertEqual([item.simplelicensing_licenseExpression for item in expressions],
                         ["Apache-2.0 WITH LLVM-exception"])

    def test_supplied_full_license_text_is_preserved(self):
        cdx = sample_cdx()
        cdx["components"][0]["licenses"] = [{
            "license": {"name": "Custom", "text": {"content": "License text."}}}]
        self.convert(cdx)
        texts = list(self.objset.foreach_type(oe.spdx30.simplelicensing_SimpleLicensingText))
        self.assertEqual([lic.simplelicensing_licenseText for lic in texts], ["License text."])

    def test_recognized_license_id_preserves_supplied_text(self):
        cdx = sample_cdx()
        cdx["components"][0]["licenses"] = [{
            "license": {"id": "Zlib", "text": {"content": "Zlib license text."}}}]
        self.convert(cdx)
        texts = list(self.objset.foreach_type(oe.spdx30.simplelicensing_SimpleLicensingText))
        expressions = list(self.objset.foreach_type(oe.spdx30.simplelicensing_LicenseExpression))
        self.assertIn("Zlib license text.", [lic.simplelicensing_licenseText for lic in texts])
        self.assertIn("Zlib", [lic.simplelicensing_licenseExpression for lic in expressions])

    def test_invalid_inventory_conversion_discards_cached_sbom(self):
        cases = (
            ([{"version": "1.0"}], "has no name"),
            ([{"name": "x", "licenses": [None]}], "Invalid license entry"),
            ([{"name": "x", "hashes": [{"alg": "SHA-256", "content": 123}]}],
             "hash content"),
        )
        for components, message in cases:
            with self.subTest(components=components):
                self.setUp()
                cdx = sample_cdx()
                cdx["components"] = components
                pool = FakePool(cdx)
                with tempfile.TemporaryDirectory() as cache:
                    path, _ = feed_sbom.fetch_sbom(
                        POOL, cache, NAME, VER, ARCH, md5=MD5, get=pool.get)

                    with self.assertRaisesRegex(feed_sbom.FeedSbomError, message):
                        feed_sbom._convert_cached_sbom(
                            self.objset, cdx, NAME, VER, ARCH, self.license_data,
                            source_url=SBOM_URL, cache_path=path)

                    self.assertFalse(os.path.exists(path))
                    self.assertFalse(os.path.exists(path + ".url"))
                    corrected_pool = FakePool()
                    retried_path, retry_url = feed_sbom.fetch_sbom(
                        POOL, cache, NAME, VER, ARCH, md5=MD5, get=corrected_pool.get)
                    self.assertEqual((retried_path, retry_url), (path, SBOM_URL))

    def test_malformed_component_hashes_are_rejected(self):
        invalid_hashes = (
            None,
            "SHA-256:abcd",
            [None],
            [{"alg": "SHA-256", "content": 123}],
            [{"alg": "SHA-256", "content": "not-hex"}],
        )
        for hashes in invalid_hashes:
            with self.subTest(hashes=hashes):
                cdx = sample_cdx()
                cdx["components"] = [{"name": "x", "hashes": hashes}]
                with self.assertRaisesRegex(feed_sbom.FeedSbomError, "hash"):
                    self.convert(cdx)

    def test_failed_conversion_after_legacy_migration_fetches_corrected_sbom(self):
        cdx = sample_cdx()
        cdx["components"] = [{"version": "1.0"}]
        pool = FakePool(cdx)
        with tempfile.TemporaryDirectory() as cache:
            legacy, source = feed_sbom.fetch_sbom(
                POOL, cache, NAME, VER, ARCH, get=pool.get)
            path, _ = feed_sbom.fetch_sbom(
                POOL, cache, NAME, VER, ARCH, md5=MD5, get=pool.get)

            with self.assertRaisesRegex(feed_sbom.FeedSbomError, "has no name"):
                feed_sbom._convert_cached_sbom(
                    self.objset, cdx, NAME, VER, ARCH, self.license_data,
                    source_url=source, cache_path=path)

            self.assertFalse(os.path.exists(legacy))
            corrected_pool = FakePool()
            retried_path, retry_url = feed_sbom.fetch_sbom(
                POOL, cache, NAME, VER, ARCH, md5=MD5, get=corrected_pool.get)
            self.assertEqual((retried_path, retry_url), (path, SBOM_URL))
            self.assertIn(SBOM_URL, corrected_pool.requests)

    def test_base64_license_text_and_invalid_encoding(self):
        cdx = sample_cdx()
        license = {"name": "Custom", "text": {"encoding": "base64", "content": "TGljZW5zZQ=="}}
        cdx["components"][0]["licenses"] = [{"license": license}]
        self.convert(cdx)
        texts = list(self.objset.foreach_type(oe.spdx30.simplelicensing_SimpleLicensingText))
        self.assertEqual([lic.simplelicensing_licenseText for lic in texts], ["License"])
        license["text"]["content"] = "not valid base64!"
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "Invalid license text"):
            self.convert(cdx)

    def test_duplicate_references_and_unsupported_content_fail(self):
        cdx = sample_cdx()
        cdx["components"][0]["bom-ref"] = "duplicate"
        cdx["components"][1]["bom-ref"] = "duplicate"
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "Duplicate"):
            self.convert(cdx)
        cdx = sample_cdx()
        cdx["services"] = [{"name": "service"}]
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "services"):
            self.convert(cdx)

    def test_mismatched_metadata_fails_conversion(self):
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "version"):
            self.convert(sample_cdx(version="wrong"))

    def test_dependencies_and_unresolved_references(self):
        cdx = sample_cdx()
        cdx["metadata"]["component"]["bom-ref"] = "main"
        cdx["components"][0]["bom-ref"] = "child"
        cdx["dependencies"] = [{"ref": "main", "dependsOn": ["child"]}]
        self.convert(cdx)
        deps = list(self.objset.foreach_filter(
            oe.spdx30.Relationship, relationshipType=oe.spdx30.RelationshipType.dependsOn))
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].from_.name, NAME)
        self.assertEqual(deps[0].to[0].name, "CPUInfo")
        cdx["dependencies"][0]["dependsOn"] = ["missing"]
        with self.assertRaisesRegex(feed_sbom.FeedSbomError, "Unresolved"):
            self.convert(cdx)

    def test_external_hook_and_default_missing_provider_behavior(self):
        import oe.spdx30_tasks

        build = self.objset.new_task_build("rootfs", "rootfs")
        with patch("oe.spdx_common.collect_direct_deps", return_value=[]), \
                patch("oe.spdx_common.collect_package_providers", return_value={}), \
                patch("bb.note") as note, patch("bb.warn") as warn:
            packages = {NAME: {"ver": VER, "arch": ARCH}}
            oe.spdx30_tasks.collect_build_package_inputs(self.d, self.objset, build, packages)
            self.assertEqual(note.call_count + warn.call_count, 1)
            package = self.convert()
            self.d.setVar("SPDX_EXTERNAL_PACKAGE_FUNC", "external_package")
            with patch("bb.utils.better_eval", return_value=package):
                oe.spdx30_tasks.collect_build_package_inputs(self.d, self.objset, build, packages)
            inputs = list(self.objset.foreach_filter(
                oe.spdx30.LifecycleScopedRelationship,
                relationshipType=oe.spdx30.RelationshipType.hasInput))
            self.assertEqual(len(inputs), 1)
            self.assertIn(package._id, inputs[0].to)

    def test_recipe_provider_does_not_invoke_external_hook(self):
        import oe.spdx30_tasks

        package = self.convert()
        self.d.setVar("SPDX_EXTERNAL_PACKAGE_FUNC", "external_package")
        build = self.objset.new_task_build("rootfs", "rootfs")
        with patch("oe.spdx_common.collect_direct_deps", return_value=[]), \
                patch("oe.spdx_common.collect_package_providers", return_value={NAME: (NAME, "hash")}), \
                patch("oe.sbom30.find_root_obj_in_jsonld", return_value=(package, self.objset)), \
                patch("bb.utils.better_eval") as external:
            oe.spdx30_tasks.collect_build_package_inputs(
                self.d, self.objset, build, {NAME: {"ver": VER, "arch": ARCH}}, {})
            external.assert_not_called()

    def test_external_hook_must_return_a_package(self):
        import oe.spdx30_tasks

        self.d.setVar("SPDX_EXTERNAL_PACKAGE_FUNC", "external_package")
        build = self.objset.new_task_build("rootfs", "rootfs")
        with patch("oe.spdx_common.collect_direct_deps", return_value=[]), \
                patch("oe.spdx_common.collect_package_providers", return_value={}), \
                patch("bb.utils.better_eval", return_value=None), \
                patch("bb.fatal", side_effect=RuntimeError) as fatal:
            with self.assertRaises(RuntimeError):
                oe.spdx30_tasks.collect_build_package_inputs(
                    self.d, self.objset, build, {NAME: {"ver": VER, "arch": ARCH}})
            self.assertIn("did not return an SPDX package", fatal.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
