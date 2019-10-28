# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
from io import StringIO
import re

from .. import libytest as YT


def parse_errors(text, error_types):
    """ Parses the provided StringIO text through the parsers
    specified by 'error_types'. The entire stdout buffer will be
    parsed, and then reset to its original position.

    For a list of valid `error_type` strings, check this module's
    ERROR_TYPES.keys(). The `error_type` parameter is order-sensitive. Handlers
    are processed in FIFO order.

    Hereafter "stderr" refers to a stringIO buffer of important error text,
    parsed from the `text` input.

    Returns: tuple of:
        ( list of error elements, list of failure elements,
         io.Stringio stderr)
    """
    # fill the `handlers` list with class pointers of the Handler class,
    # specified by name in the error_types collection.
    handlers = []
    for _type in error_types:
        handlers.append(ERROR_TYPES[_type])

    # copy the input text into a secondary buffer. We expect handlers to remove
    # lines from the buffer which they have consumed
    pos_original = text.tell()
    text.seek(0)
    text_copy = text.readlines()
    text.seek(pos_original)

    ret_elements = []
    for handler in handlers:
        elements, removals = handler.handle(text_copy)
        ret_elements.extend(elements)
        Handler.remove_indexes(text_copy, removals)

    return ret_elements

############
# Handlers #
############

class Handler():

    @staticmethod
    def handle(lines):
        raise NotImplementedError


    def remove_indexes(lines, removals):
        offset = 0
        for removal in sorted(removals):
            del lines[removal - offset]
            offset += 1

class BootHandler(Handler):
    """This class looks for common boot warnings and failures about devices not
       being found and services not starting.
    """
    RE_NOT_FOUND = re.compile(r'\ not found', re.M | re.A | re.I)
    RE_CANNOT = re.compile(r'\b(can\'t|cannot)\b', re.M | re.I)

    @staticmethod
    def handle(lines):
        elements = []
        removals = []
        for l in range(0, len(lines)):
            line = lines[l]
            if BootHandler.RE_NOT_FOUND.search(line):
                elements.append(YT.Error(line, 'boot'))
            if BootHandler.RE_CANNOT.search(line):
                elements.append(YT.Error(line, 'boot'))
            else:
                continue
            removals.append(l)

        return elements, removals


class GenericHandler(Handler):
    RE_FAILURE_GENERAL = re.compile(r'\b(fail(ed|ure)?)s?\b', re.I | re.M)
    RE_ERROR_GENERAL = re.compile(r'\b(error)(ed|s)?\b', re.I | re.M)
    RE_EXCEPTION_GENERAL = re.compile(r'\b(except)(ion)?\b', re.I | re.M)
    RE_WRONG_GENERAL = re.compile(r'\b(wrong)(ly)?\b', re.I | re.M)

    @staticmethod
    def handle(lines):
        elements = []
        removals = []
        for l in range(0, len(lines)):
            line = lines[l]
            if GenericHandler.RE_ERROR_GENERAL.search(line):
                elements.append(YT.Error(line, 'generic'))
            elif GenericHandler.RE_FAILURE_GENERAL.search(line):
                elements.append(YT.Failure(line, 'generic'))
            elif GenericHandler.RE_EXCEPTION_GENERAL.search(line):
                elements.append(YT.Error(line, 'generic'))
            elif GenericHandler.RE_WRONG_GENERAL.search(line):
                elements.append(YT.Error(line, 'generic'))
            else:
                continue
            removals.append(l)

        return elements, removals


class PythonHandler(Handler):

    RE_STACKTRACE_START = re.compile(r'^Traceback \(most recent call last\)\:')
    RE_STACKTRACE_END = re.compile(r'^\S+\:.*')

    @staticmethod
    def claim(line):
        if self.RE_STACKTRACE_START.match(line):
            return True
        return False

    def handle(lines):
        elements = []
        e_stack = None
        removals = []

        for l in range(0, len(lines)):
            line = lines[l]
            if PythonHandler.RE_STACKTRACE_START.match(line):
                e_stack = StringIO()

            if e_stack is not None:
                if PythonHandler.RE_STACKTRACE_END.match(line):
                    e_stack.seek(0)
                    elements.append(YT.Error(e_stack.read(), 'salt'))
                    e_stack = None
                removals.append(l)

        return elements, removals


from pprint import pprint
class ShellHandler(Handler):
    RE_BASH_LINE = re.compile(r'^[\/\w]+\: line \d+\:.*$', re.M)
    RE_NO_FILE = re.compile(r'\bno such file\b(\sor directory)?', re.I)

    @staticmethod
    def handle(lines):
        elements = []
        removals = []
        for l in range(0, len(lines)):
            line = lines[l]
            if ShellHandler.RE_BASH_LINE.match(line):
                elements.append(YT.Failure(line, 'shell'))
            elif ShellHandler.RE_NO_FILE.search(line):
                elements.append(YT.Failure(line, 'shell'))
            else:
                continue
            removals.append(l)

        return elements, removals


ERROR_TYPES = {\
    'python':   PythonHandler,
    'shell' : ShellHandler,
    #'dmesg' : DmesgHandler,
    'boot':     BootHandler,
    'generic' : GenericHandler,
    }
