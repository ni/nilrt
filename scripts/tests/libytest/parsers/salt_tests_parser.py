# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import io
import re

from .ptest_parser import PTestParser
from .error_parsers import parse_errors
from .. import libytest as YT

class SaltTestsParser(PTestParser):
    """Parses the salt-testing ptest output."""

    OUTPUT_BIAS_ABOVE = False
    RE_RESULT_NAME = re.compile(r'^([^\(]+)\s\(([^\)]+)\)')
    # these headings are really annoying
    RE_HEADING = re.compile(r'^~+', re.M)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.suite_name = 'salt-ptests'

    def _classname_from_match(self, match):
        name_match = self.RE_RESULT_NAME.match(match.groups()[1])
        return '.'.join([self.suite_name, name_match.groups()[1]])

    @classmethod
    def is_owner(self, suite_name, suite_path, *args, **kwargs):
        if suite_name in ['salt', 'salt-testing', 'salt-tests', 'salt-ptests']:
            return True
        else:
            return False

    def _name_from_match(self, match):
        return self.RE_RESULT_NAME.match(match.groups()[1]).groups()[0]

    def parse(self, console, timestamps):
        # remove the annoying salt headings from the test output
        subconsole = io.StringIO()
        console.seek(0)
        in_heading = False
        for line in console.readlines():
            if self.RE_HEADING.match(line):
                if in_heading:
                    in_heading = False
                    continue
                else:
                    in_heading = True
            if not in_heading:
                subconsole.write(line)

        return super().parse(subconsole, timestamps)

    def _parse_test_stdout(self, e_test, match, stdout):
        elements = parse_errors(stdout, ['python', 'generic'])
        e_test.add_children(elements)

        stdout.seek(0)
        stdout_stripped = stdout.read().strip()
        if len(stdout_stripped) > 0:
            e_test.stdouts.append(YT.StdOut(stdout_stripped))
