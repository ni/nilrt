# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import io
import re

from .. import libytest as YT

from .error_parsers import parse_errors

class PTestParser():

    # The side of the test/subtest result line on which stdout/stderr
    # are written. True, for above; False, for below.
    OUTPUT_BIAS_ABOVE = True

    RE_RESULT_LINE = re.compile(r'^(PASS|FAIL|SKIP)\:\s(.+)$')
    RE_RESULT_LINE_SUBTEST = re.compile(r'^(PASS|FAIL|SKIP)\:\s((\S+)\s+(\d+)\s+\-\s+(.+))$')
    RE_GENERAL_FAILURE = re.compile(r'(.*fail(?:ed)?.*)$', flags=re.IGNORECASE)
    RE_GENERAL_ERROR = re.compile(r'(.*error(?:ed)?.*)$', flags=re.IGNORECASE)
    RE_GENERAL_TIMEOUT = re.compile(r'(.*timed?-?out.*$)', flags=re.IGNORECASE)

    def __init__(self):
        self.suite_name = 'generic'

    def _best_result_match(self, line):
        """Perform a result line match on the line, if it is successful,
        check also for a subtest, if that test is successful, return
        that instead.
        """
        match = self.RE_RESULT_LINE.match(line)
        if not match:
            return None
        match_subtest = self.RE_RESULT_LINE_SUBTEST.match(line)
        if match_subtest:
            return match_subtest
        else:
            return match

    def _classname_from_match(self, match):
        return ".".join([self.suite_name, 'ptest'])

    def gen_suite_testcase(self, e_suite, test_path):
        e_test = YT.TestCase()
        full_name = test_path.pop(-1)
        full_classname = '.'.join([self.suite_name, 'ptest'] + test_path)
        e_test.set('name', full_name)
        e_test.set('classname', full_classname)
        return e_test

    @classmethod
    def is_owner(self, suite_name, suite_path, *args, **kwargs):
        return True

    def _name_from_match(self, match):
        name = ' '.join(match.groups()[2:])
        return match.groups()[1]

    def parse(self, console, timestamps):
        console.seek(0)

        output_units = [[None, io.StringIO()]]

        for line in console:
            match = self._best_result_match(line)
            if match:
                if self.OUTPUT_BIAS_ABOVE:
                    output_units[-1][0] = match
                    output_units.append([None, io.StringIO()])
                else:
                    output_units.append([match, io.StringIO()])
            else:
                output_units[-1][1].write(line)

        e_suite = YT.TestSuite(name=self.suite_name)
        for unit in output_units:
            result = unit[0]
            stdout = unit[1]
            if result is None:
                self._parse_suite_stdout(e_suite, stdout)
                continue

            # Generate the test case
            e_test = YT.TestCase()
            self._parse_test_result(e_test, result, stdout)
            self._parse_test_stdout(e_test, result, stdout)
            e_suite.test_cases.append(e_test)

        # set timestamps
        self._parse_timestamps(e_suite, timestamps)

        return e_suite

    def _parse_suite_stdout(self, e_suite, stdout):
        stdout.seek(0)
        elements = parse_errors(stdout, ['generic'])
        # Create an 'execution' pseudo-testcase to house general errors
        # and failures with the testsuite.
        if elements:
            e_suite_testcase = self.gen_suite_testcase(e_suite, ['execution'])
            e_suite_testcase.add_children(elements)
            e_suite.test_cases.append(e_suite_testcase)

        for line in stdout:
            e_suite.stdout += line

    def _parse_test_result(self, e_test, match, stdout):
        stdout.seek(0)

        full_name = self._name_from_match(match)
        full_classname = self._classname_from_match(match)

        e_test.set('name', full_name)
        e_test.set('classname', full_classname)

        status = YT.norm_status(match.groups()[0])
        if len(e_test.failures) == 0 and status == 'FAIL':
            # Since we don't know how it failed, make a failure element
            # from stdout.
            failure = YT.Failure('FAIL', 'ptest', stdout.read())
            e_test.failures.append(failure)
        elif status == 'SKIP':
            e_test.skipped = True

    def _parse_test_stdout(self, e_test, match, stdout):
        elements = parse_errors(stdout, ['generic'])
        e_test.add_children(elements)

        stdout.seek(0)
        output = stdout.read().strip()
        if len(output) > 0:
            e_test.stdouts.append(YT.StdOut(stdout.read()))

    def _parse_timestamps(self, e_suite, timestamps):
        if timestamps[0] is not None:
            e_suite.set('timestamp', timestamps[0])
            if timestamps[1] is not None:
                delta = timestamps[1] - timestamps[0]
                e_suite.set('time', delta)
