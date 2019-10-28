#!/usr/bin/env python3

import argparse
import io
import os
import re
import sys

from .parsers import PTestRunnerParser, ConsoleParser
from .mask import Mask
from . import libytest as YT

class Application():
    """CLI Application class
    """

    def __init__(self, args):
        self.config = args
        self.mask = None

    def main(self):
        if self.config.mask_file:
            self.load_mask_file()

        suites = []
        for console in self.config.console_file:
            suites.append(self.parse_console_file(console))
        e_suites = self.merge_suites(*suites)

        rc = 0

        if self.mask:
            removals = self.mask.mask_expectations(e_suites)
            if self.config.verbose:
                self._print_mask_removals(removals)

        if getattr(self.config, 'grepable', False):
            self.print_testsuites_grepable(e_suites)
        elif self.config.verbose:
            self.print_testsuites_digest(e_suites)

        self.write_xml(e_suites)

        return rc

    def eval_masks(self, results):
        rc = 0
        for suite, items in results.items():
            for item in items:
                if item[3] is False:
                    rc += 1
        return rc

    def load_mask_file(self):
        self.mask = Mask()
        if self.config.verbose:
            print("Loading mask file: {}".format(self.config.mask_file))
        self.mask.load_mask_file(self.config.mask_file)
        print(self.mask)

    def merge_suites(self, *suites):
        e_ret = YT.TestSuites()
        for element in suites:
            if isinstance(element, YT.TestSuites):
                e_ret.test_suites.extend(element.test_suites)
            elif isinstance(element, YT.TestSuite):
                e_ret.test_suites.append(element)
            else:
                raise ValueError("suite element is not a TestSuite or "
                                 "TestSuites collection.")
        return e_ret

    def parse_console(self, console, console_name=None):
        parser_console = ConsoleParser()
        parser_ptest_runner = PTestRunnerParser()
        suites = []  # TestSuites accumulator (for later merging)

        # find the ptest runner segments of the console log (if any)
        ptest_segments = parser_ptest_runner.find_runner_segments(console)

        # Parse Ptest Runner segments (if present)
        for seg in ptest_segments:
            subconsole = io.StringIO()

            console.seek(seg[0])
            subconsole.write(console.read(seg[1] - seg[0]))
            suites.append(parser_ptest_runner.parse(subconsole))

        if not getattr(self.config, 'ptest_only', False):
            # Parse the remainder of the console
            console_suites = []
            for i in range(0, len(ptest_segments) + 1):
                if i == 0:
                    start = 0
                else:
                    start = ptest_segments[i-1][1]
                try:
                    end = ptest_segments[i][0]
                except IndexError:
                    end = None
                subconsole = io.StringIO()
                console.seek(start)

                if end is not None:
                    subconsole.write(console.read(end - start))
                else:
                    subconsole.write(console.read())

                console_suites.extend(parser_console.parse(subconsole).test_suites)
            suites.append(parser_console.merge_console_testsuites(*console_suites))

        e_suites = self.merge_suites(*suites)
        # if console_name is asserted, add a property to each testsuite that
        # expresses that name
        if console_name:
            for e_suite in e_suites.test_suites:
                e_prop_name = YT.Property('console-name', console_name)
                e_suite.properties.append(e_prop_name)

        return e_suites

    def parse_console_file(self, filepath):
        if self.config.verbose:
            print("Parsing {}...".format(filepath))

        console = io.StringIO()
        with open(filepath, 'r', encoding='utf-8', errors='replace',
                  newline='') as fp_console:
            console.write(fp_console.read())

        #self.sanitize_console(console)
        e_suites = self.parse_console(console, filepath)
        return e_suites

    def _print_mask_removals(self, removals):
        print("Masked-out %d entries." % len(removals))

    def print_masks(self, results):
        print('\nExpect operation output:')

        for suite, items in results.items():
            for item in items:
                print('{:4} |'.format('OK' if item[3] else 'FAIL'), end="")
                if self.config.verbose:
                    print(' {} vs. {} |'.format(item[1], item[2]), end="")
                print(' ', item[0])

    def print_testsuites_digest(self, e_suites):
        print("[ {} ]".format(e_suites.get_digest()))
        for e_suite in e_suites.test_suites:
            print("  |-> [ {} ]".format(e_suite.get_digest()))

    def print_testsuites_grepable(self, e_suites):
        for e_suite in e_suites.test_suites:
            print(e_suite.get_digest_grep())

    @classmethod
    def sanitize_console(self, console):
        RE_ANSI_CONTROL = re.compile(r'\x1b[^m]*m')
        RE_CARRIAGE_RETURN = re.compile('\r')
        console.seek(0)
        mirror = console.read()
        console.write(RE_CARRIAGE_RETURN.sub('', mirror))
#        for line in console:
#            RE_ANSI_CONTROL.sub('', line)
#            RE_CARRIAGE_RETURN.sub('', line)

    def write_xml(self, root):
        if self.config.verbose:
            print("Writing results to: {}...".format(self.config.output_file))
        fp_out = open(self.config.output_file, 'wb')
        YT.write_xml(root, fp_out, verbose=self.config.verbose_output)
        fp_out.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--grepable', action='store_true',
                        help='Output runtime information in a more grep-friendly fashion')
    parser.add_argument('-m', '--mask-file', action='store',
                        help="Mask file")
    parser.add_argument('-p', '--ptest-only', action='store_true',
                        help='Only process the ptest-runner section, if one is available.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Enable more verbose output.")
    parser.add_argument('--verbose-output', action='store_true',
                        help='Print xml tags which are not required by junit, even if empty.')
    parser.add_argument('console_file', nargs='+',
                        help="ptest-runner2 console to parse.")
    parser.add_argument('output_file', action='store', help="Output file")
    args = parser.parse_args()

    app = Application(args)
    sys.exit(app.main())
