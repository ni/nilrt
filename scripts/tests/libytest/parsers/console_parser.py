import datetime
import io
import os.path
import re

from .. import libytest as YT

from .error_parsers import parse_errors

class ConsoleParser():

    RE_GENERAL_FAILURE = re.compile(r'(.*fail(?:ed)?.*)$',  flags=re.IGNORECASE)
    RE_GENERAL_ERROR   = re.compile(r'(.*error(?:ed)?.*)$', flags=re.IGNORECASE)
    RE_GENERAL_TIMEOUT = re.compile(r'(.*timed?-?out.*$)',  flags=re.IGNORECASE)

    SUITE_NAME = 'general'

    def __init__(self):
        self.suite_name = ConsoleParser.SUITE_NAME

    def add_timeout_failure(self, parser, e_suite):
        e_tc_timeliness = parser.gen_suite_testcase(e_suite, ['timeliness'])
        e_tc_timeliness.add_failure(YT.Failure('timeout', 'ptest'))
        e_suite.test_cases.append(e_tc_timeliness)

    def choose_parser(self, suite_name, suite_path):
        for type_ in PARSER_TYPES:
            if type_.is_owner(suite_name, suite_path):
                return type_

    @classmethod
    def extract_suite_name(self, console):
        for line in console:
            match = self.RE_PTEST_START.match(line)
            if match:
                path = match.group(1)
                path, tail = os.path.split(path)
                if tail == 'ptest':
                    return os.path.basename(path), match.group(1)
                else:
                    return tail, match.group(1)

    @classmethod
    def extract_timestamp(self, console):
        for line in console:
            match = self.RE_RUNNER_TIMESTAMP.match(line)
            if match:
                groups = [int(t) for t in match.groups() if t is not None]
                ts = datetime.datetime(*groups).timestamp()
                return ts
        return None

    @classmethod
    def merge_console_testsuites(self, *console_testsuites):
        e_return = YT.TestSuite(name=ConsoleParser.SUITE_NAME)
        tcases = []
        for testsuite in console_testsuites:
            # children
            tcases.extend(testsuite.test_cases)
            e_return.properties.extend(testsuite.properties)
            e_return.stdout.text += testsuite.stdout.text
            e_return.stderr.text += testsuite.stderr.text
            # attributes
            testsuite.eval_counts()
            e_return.set('time', e_return.get('time') + testsuite.get('time'))

        e_return.test_cases = YT.merge_testcases(*tcases)
        return e_return

    def parse(self, console):
        console.seek(0)

        e_suites = YT.TestSuites()
        e_suite = YT.TestSuite(name=ConsoleParser.SUITE_NAME)

        # encapsulating test case for general errors
        e_test = YT.TestCase(name='general', classname=self.suite_name)
        elements = parse_errors(console, [
            'python',
            'shell',
            'boot',
            'generic',
        ])
        e_test.add_children(elements)
        e_test.eval_status()

        e_suite.test_cases.append(e_test)
        e_suites.test_suites.append(e_suite)

        return e_suites

    def _parse_runner(self, console, name='ptests'):
        e_suites = YT.TestSuites()
        suite_id = 0
        while True:
            timeout = False
            # Starting Timestamp
            ts_start = self.extract_timestamp(console)
            if ts_start is None:
                break
            # Ptest START
            subconsole = self.read_until(console, self.RE_PTEST_START)
            suite_name, suite_path = self.extract_suite_name(subconsole)
            # Ptest stdout
            parser_type = self.choose_parser(suite_name, suite_path)
            subconsole = self.read_until(console, (self.RE_PTEST_END,
                                                   self.RE_PTEST_TIMEOUT),
                                                   False)
            # PTest END/TIMEOUT
            if self.is_timeout(self.read_until(console, (self.RE_PTEST_END,
                                                         self.RE_PTEST_TIMEOUT),
                                                         True)):
                timeout = True
            # Ending Timestamp
            ts_end = self.extract_timestamp(console)
            if ts_start is None:
                raise RuntimeError("Malformed ptest runner output")
            # Parse Ptest
            parser = parser_type()
            parser.suite_name = suite_name
            e_suite = parser.parse(subconsole, (ts_start, ts_end))
            if timeout:
                self.add_timeout_failure(parser, e_suite)
            # Cleanup and save
            e_suite.set('id', suite_id)
            suite_id += 1
            e_suites.test_suites.append(e_suite)

        e_suites.set('name', name)
        return e_suites

    @classmethod
    def read_until(self, console, re_stops, inclusive=True):
        """Reads an io.StringIO buffer 'console' until a line that
        matches any entry in 're_stops'. If 'inclusive' is asserted,
        the matching line is included in the returned buffer. If
        'inclusive' is True, the buffer of 'console' is set to
        immediately after the matching line; else, it is immediately
        before the matching line.

        Returns: io.StringIO subconsole of all lines reada and,
                 optionally, the stop line.
        """
        if not isinstance(re_stops, (list, tuple)):
            re_stops = (re_stops,)
        subconsole = io.StringIO()
        marker = console.tell()
        line = console.readline()
        while line:

            # Match on any of the stop regexes in re_stops
            match = None
            for re_stop in re_stops:
                match = re_stop.match(self.clean_ansi_control(line))
                if match:
                    break

            if match:
                if inclusive:
                    subconsole.write(line)
                else:
                    console.seek(marker)
                break

            subconsole.write(line)
            marker = console.tell()
            line = console.readline()
        subconsole.seek(0)
        return subconsole

    @classmethod
    def subconsole(self, source, end, start=None):
        subconsole = io.StringIO()
        if start:
            source.seek(start)
        else:
            start = source.tell()
        marker = source.tell()
        line = source.readline()
        subconsole.write(source.read(end - start))
        subconsole.seek(0)
        return subconsole

    @classmethod
    def seek_to(self, source, re_stop, inclusive=True):
        marker = source.tell()
        line = source.readline()
        while line:
            match = re_stop.match(line)
            if match:
                if inclusive:
                    return source.tell()
                else:
                    return marker
            marker = source.tell()
            line = source.readline()
        return source.tell()
