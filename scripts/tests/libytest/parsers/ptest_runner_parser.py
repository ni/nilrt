import datetime
import io
import os.path
import re

from .. import libytest as YT

from .glibc_parser import GlibcParser
from .kernel_tests_parser import KernelTestsParser
from .ptest_parser import PTestParser
from .rt_tests_parser import RTTestsParser
from .salt_tests_parser import SaltTestsParser

class PTestRunnerParser():

    RE_RUNNER_START = re.compile(r'^START:\sptest-runner')
    RE_RUNNER_END = re.compile(r'^STOP:\sptest-runner')
    RE_RUNNER_TIMESTAMP = \
        re.compile(r'^(\d{4})\-(\d{2})-(\d{2})T(\d{2})\:(\d{2})\:?(\d{2})?')
    RE_PTEST_START = re.compile(r'^BEGIN:\s(\S+)')
    RE_PTEST_END = re.compile(r'^END:\s(\S+)')
    RE_PTEST_TIMEOUT = re.compile(r'^TIMEOUT:\s(\S+)')

    RE_ANSI_ESCAPE = re.compile(r'\x1b[^m]*m')

    PTEST_PARSER_TYPES = [\
        GlibcParser,
        KernelTestsParser,
        RTTestsParser,
        SaltTestsParser,
        PTestParser,  # must be the last in this sequence
    ]

    def __init__(self):
        pass

    def add_timeout_failure(self, parser, e_suite):
        e_tc_timeliness = parser.gen_suite_testcase(e_suite, ['timeliness'])
        #e_tc_timeliness.add_failure(YT.Failure('timeout', 'ptest'))
        e_tc_timeliness.failures.append(YT.Failure('timeout', 'ptest'))
        e_suite.test_cases.append(e_tc_timeliness)

    def choose_parser(self, suite_name, suite_path):
        for type_ in self.PTEST_PARSER_TYPES:
            if type_.is_owner(suite_name, suite_path):
                return type_

    @classmethod
    def clean_ansi_control(self, line):
        return self.RE_ANSI_ESCAPE.sub('', line)

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
    def find_runner_segments(self, console):
        segments = []
        segment = [None, None]
        in_segment = False
        console.seek(0)

        while True:
            segment[0] = self.seek_to(console, self.RE_RUNNER_START, False)
            segment[1] = self.seek_to(console, self.RE_RUNNER_END, True)
            if segment[0] is not None and segment[1] is not None:
                segments.append(segment)
                segment = [None, None]
                continue
            elif segment[0] is not None and segment[1] is None:
                console.seek(0, io.SEEK_END)
                segment[1] = console.tell()
                segments.append(segment)
                segment = [None, None]
                continue
            else:
                break

        return segments

    def is_timeout(self, console):
        for line in console:
            line = self.RE_ANSI_ESCAPE.sub('', line)
            if self.RE_PTEST_TIMEOUT.match(line):
                return True
        return False

    def parse(self, console):
        console.seek(0)
        # pre-runner
        subconsole = self.read_until(console, self.RE_RUNNER_START, False)
        # PTEST RUNNER
        # consume, but do not use, the START: line
        self.read_until(console, self.RE_RUNNER_START)
        subconsole = self.read_until(console, self.RE_RUNNER_END, False)
        e_suites = self._parse_runner(subconsole)
        # post-runner (Do nothing)
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
        while len(line) > 0:
            match = re_stop.match(line)
            if match:
                if inclusive:
                    return source.tell()
                else:
                    return marker
            marker = source.tell()
            line = source.readline()
        return None
