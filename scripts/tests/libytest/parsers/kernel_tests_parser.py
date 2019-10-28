# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
from .ptest_parser import PTestParser

class KernelTestsParser(PTestParser):

    OUTPUT_BIAS_ABOVE = True

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.suite_name = 'kernel-tests'

    @classmethod
    def is_owner(self, suite_name, suite_path, *args, **kwargs):
        if suite_name in ['kernel-tests']:
            return True
        else:
            return False
