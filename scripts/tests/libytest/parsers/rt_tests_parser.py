# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
from .ptest_parser import PTestParser

class RTTestsParser(PTestParser):

    OUTPUT_BIAS_ABOVE = True

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.suite_name = 'rt-tests'

    @classmethod
    def is_owner(self, suite_name, suite_path, *args, **kwargs):
        if suite_name in ['rt-tests']:
            return True
        else:
            return False
