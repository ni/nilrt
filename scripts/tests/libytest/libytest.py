#!/usr/bin/env python3
# vi: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# ---
# The schema used in this library is a union of the "xUnit XML Template" from
# the Yocto Project[1] and the "junit-jenkins" schema defined by some rando[2]
# (which seems to be what the jenkins xUnit parser uses internally. In general,
# the Yocto standard is a slightly expanded and intensive version of the junit
# standard.
# [1] https://wiki.yoctoproject.org/wiki/QA/xUnit_XML_Template
# [2] https://raw.githubusercontent.com/bluebird75/luaunit/master/junitxml/junit-jenkins.xsd

from collections import OrderedDict
from copy import deepcopy
import datetime
import lxml.etree as ET

ISOFORMAT = "%Y-%m-%dT%H:%M:%S"
STATUS = {
    'PASS': ('P', 'PASS', 'PASSED'),
    'FAIL': ('F', 'FAIL', 'FAILED'),
    'SKIP': ('S', 'SKIP', 'SKIPPED'),
}


#================#
# MODULE METHODS #
#================#

def merge_testcases(*testcases):
    """Examines the sequence of TestCase objects in the parameters. If any two
    testcases have the same `classname` AND `name`, they are merged in to a
    single testcase object.
    """
    mappings = OrderedDict()
    for case in testcases:
        fq_name = (case.get('classname'), case.get('name'))
        try:
            mappings[fq_name].append(case)
        except KeyError:
            mappings[fq_name] = [case]

    for names, cases in mappings.items():
        if len(cases) == 0:
            continue
        new_case = TestCase(classname=names[0], name=names[1])
        new_case.skipped = True
        for case in cases:
            new_case.errors.extend(case.errors)
            new_case.failures.extend(case.failures)
            new_case.stdouts.extend(case.stdouts)
            new_case.stderrs.extend(case.stderrs)
            if case.skipped == False:
                new_case.skipped = False
            new_case.set('time', new_case.get('time') + case.get('time'))
        mappings[names] = [new_case]

    return [cases[0] for cases in mappings.values()]

def norm_status(text):
    for status, strings in STATUS.items():
        if text.upper() in strings:
            return status
    else:
        return None

def sanitize_str_xml(text, no_newlines=False):
    """Returns an instance of the input text with all characters
    which comply with the xml1.0 charset specification. ie. no
    NULL characters, ASCII control characters (except newline), etc.
    text : str input text
    """
    def is_valid_xml_char(c):
        c = ord(c)
        if not no_newlines and c in (0x9, 0xA):
            return True
        else:
            return (0x20 <= c <= 0xD7FF
                    or 0xE000 <= c <= 0xFFFD or 0x10000 <= c <= 0x10FFFF)
    return ''.join(char for char in text if is_valid_xml_char(char))

def _status_handler(value):
    value = value.upper()
    for key, values in STATUS.items():
        if value in values:
            return key
    raise ValueError("Cannot parse status value '{}'.".format(value))


def _str_timestamp(value):
    return datetime.datetime.fromtimestamp(value).strftime(ISOFORMAT)

def suites_to_string(e_suites, verbose=False):
    return ET.tostring(e_suites.get_xml_element(verbose),
                       encoding='utf-8', pretty_print=True)

def write_xml_file(e_suites, filepath, verbose=False):
    with open(filepath, 'wb') as fp_out:
        write_xml(e_suites, fp_out, verbose)

def write_xml(e_suites, fp_out, verbose=False):
    _write_xml_header(fp_out)
    #fp_out.write(ET.tostring(e_suites.get_xml_element(verbose),
                             #encoding='utf-8', pretty_print=True))
    fp_out.write(suites_to_string(e_suites, verbose))

def _write_xml_header(fp_out):
    fp_out.write(b'<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n')


#================#
# MODULE CLASSES #
#================#


class Spec():
    def __init__(self, type_handler, is_required, default_value,
                 str_handler=None):
        self.default_value = default_value
        self.required = bool(is_required)
        self.str_handler = str_handler
        self.type_handler = type_handler
        self.value = None

    def get(self):
        if self.value is not None:
            return self.value
        else:
            return self.default_value

    def satisfied(self):
        if not self.required:
            return True
        elif self.value is not None:
            return True
        else:
            return False

    def set(self, value):
        self.value = self.type_handler(value)

    def __str__(self):
        try:
            return self.str_handler(self.get())
        except TypeError:
            return str(self.get())


#===============#
# BASE CLASSSES #
#===============#


class DatetimeWrapper(datetime.datetime):

    def __new__(self, *args, **kwargs):
        if args[0] is None:
            return super().now()

        try:
            return super().fromtimestamp(args[0].timestamp())
        except AttributeError:
            pass
        return super().__new__(*args, **kwargs)


class Element():

    def __init__(self, *args, **kwargs):
        # deepcopy the ATTR specs so that they can be modified by this
        # instance.
        self.ATTRS = deepcopy(self.ATTRS)

        for key, value in kwargs.items():
            try:
                self.set(key, value)
            except KeyError:
                pass

    def get(self, attr):
        return self.ATTRS[attr].get()

    def get_children(self):
        return []

    def get_xml_element(self, verbose=False):
        attrs = {}
        for attr, spec in self.ATTRS.items():
            if not spec.satisfied():
                raise RuntimeError("{} ({}) attribute: '{}' is required but "
                                   "unset.".format(self.TAG, id(self), attr))
            if not verbose and spec.value is None:
                continue
            else:
                attrs[attr] = str(spec)

        try:
            e = ET.Element(self.TAG, attrs)
        except ValueError as exception:
            print(self.TAG, attrs)
            raise exception

        try:
            for child in self._children:
                e.append(child.get_xml_element(verbose))
        except AttributeError:
            pass

        try:
            e.text = self.formatted_text()
        except (AttributeError, ValueError):
            pass

        return e

    def reset(self, attr):
        try:
            self.ATTRS[attr].set(self.ATTRS[attr].default_value)
        except KeyError:
            raise KeyError("'{}' is not a defined attribute of {}".format(attr,
                           type(self)))

    def set(self, attr, value):
        if isinstance(value, str):
            value = sanitize_str_xml(value, no_newlines=False)

        try:
            self.ATTRS[attr].set(value)
        except KeyError:
            raise KeyError("'{}' is not a defined attribute of {}".format(attr,
                           type(self)))

    def __str__(self):
        return ET.tostring(self.get_xml_element(), encoding=str)


#=================#
# DERIVED CLASSES #
#=================#


class CData(Element):

    ATTRS={}

    def __init__(self, text="", **kwargs):
        self.text = text
        super().__init__(**kwargs)

    def get_xml_element(self, verbose=False):
        e = super().get_xml_element(verbose)
        return e

    def formatted_text(self):
        if len(self.text) > 0:
            return ET.CDATA(self.text)
        else:
            return self.text

    @property
    def text(self):
        if self.__text is None:
            return ""
        else:
            return self.__text

    @text.setter
    def text(self, value):
        if value is None:
            self.__text = ""
        else:
            self.__text = sanitize_str_xml(value)

    def __add__(self, other):
        if isinstance(other, str):
            return type(self)(self.text + other)
        elif isinstance(other, CData):
            return type(self)(self.text + other.text)
        raise ValueError()

    def __iadd__(self, other):
        if isinstance(other, str):
            self.text = self.text + other
        elif isinstance(other, CData):
            self.text += other.text
        return self


class Error(CData):

    TAG = "error"
    ATTRS = {
        'message': Spec(str, True, ""),
        'type'   : Spec(str, True, ""),
    }

    def __init__(self, message, type_, text=None, *args, **kwargs):
        kwargs['message'] = str(message)
        kwargs['type'] = str(type_)
        super().__init__(**kwargs)


class Failure(CData):
    """A failure element contains information about why a testcase's assertions
       were not met. It is different from an Error in that the presence of
       Failure elements indicates that a TestCase has 'FAIL'ed.
    """

    TAG = 'failure'
    ATTRS = {
        'message': Spec(str, True, ""),  # The failing assertion or text
        'type'   : Spec(str, True, ""),
    }

    def __init__(self, message, type_, text=None, *args, **kwargs):
        kwargs['message'] = sanitize_str_xml(str(message))
        kwargs['type'] = str(type_)
        super().__init__(**kwargs)


class Properties(Element):

    TAG = "properties"
    ATTRS = {}

    def __init__(self, *args, **kwargs):
        self._children = []
        for arg in args:
            if isinstance(arg, list):
                self._children.extend(arg)
            elif isinstance(arg, Property):
                self._children.append(arg)
            else:
                raise TypeError(arg)

    def get_children(self):
        return self._children


class Property(Element):

    TAG = "property"
    ATTRS = {\
        'name' : Spec(str, True, ""),
        'value': Spec(str, True, "")}

    def __init__(self, name, value, *args, **kwargs):
        kwargs['name'] = name
        kwargs['value'] = value
        super().__init__(*args, **kwargs)


class Skipped(Element):

    TAG = "skipped"
    ATTRS = {}


class StdErr(CData):

    TAG = "system-err"
    ATTRS = {}


class StdOut(CData):

    TAG = "system-out"
    ATTRS = {}


class TestCase(Element):

    TAG = 'testcase'
    ATTRS = {\
        'assertions': Spec(int, False, 0),
        'classname' : Spec(str, True, ""),
        'name'      : Spec(str, True, ""),
        'status'    : Spec(_status_handler, False, 'FAIL'),
        'time'      : Spec(int, False, 0),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self._errors = []
        self._failures = []
        self._skipped = False
        self._stdouts = []
        self._stderrs = []

    def add_child(self, child):
        if isinstance(child, Error):
            self.errors.append(child)
        elif isinstance(child, Failure):
            self.failures.append(child)
        elif isinstance(child, StdErr):
            self.stderrs.append(child)
        elif isinstance(child, StdOut):
            self.stdouts.append(child)
        else:
            raise ValueError('child element is of an invalid type. Found '
                             '%s.' % type(child))

    def add_children(self, children):
        for child in children:
            self.add_child(child)

    @property
    def errors(self):
        return self._errors

    @property
    def failures(self):
        return self._failures

    @property
    def skipped(self):
        return self._skipped

    @skipped.setter
    def skipped(self, value):
        self._skipped = bool(value)

    @property
    def stdouts(self):
        return self._stdouts

    @property
    def stderrs(self):
        return self._stderrs

    def eval_counts(self):
        self.reset('assertions')
        self.set('assertions', len(self.failures))

    def eval_status(self):
        status = 'PASS'
        if len(self.failures) > 0:
            status = 'FAIL'
        elif self.skipped:
            status = 'SKIP'
        self.set('status', status)

    def get_xml_element(self, verbose=False):
        self._children = []
        self.eval_status()
        self.eval_counts()

        if self.skipped:
            self._children.append(Skipped())

        # NOTE: the order of child elements here is strictly defined by the
        # schema. No; I don't know why.
        for group in ['errors', 'failures']:
            if verbose or len(getattr(self, group)) > 0:
                self._children.extend(getattr(self, group))
        for group in ['stdouts', 'stderrs']:
            for item in getattr(self, group):
                # only print the std{out/err} if it is non-zero length or if
                # verbose
                if verbose or len(item.text) > 0:
                    self._children.append(item)
        return super().get_xml_element(verbose)


class TestSuite(Element):

    TAG = 'testsuite'
    ATTRS = {\
        'disabled' : Spec(int, False, 0),
        'errors'   : Spec(int, False, 0),
        'failures' : Spec(int, False, 0),
        'hostname' : Spec(str, False, "localhost"),
        'id'       : Spec(int, False, -1),
        'name'     : Spec(str, True, ""),
        'package'  : Spec(str, False, ""),
        'skipped'  : Spec(int, False, 0),
        'tests'    : Spec(int, True, 0),
        'time'     : Spec(int, False, 0),
        'timestamp': Spec(int, False, 0, _str_timestamp),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.test_cases = []
        self.properties = []
        # Unlike TestCases, TestSuites are only supposed to have max 1 stdout &
        # stderr element.
        self.stdout = StdOut()
        self.stderr = StdErr()
        self.eval_counts()

    def eval_counts(self):
        self.reset('tests')
        self.reset('errors')
        self.reset('failures')
        self.reset('skipped')
        self.reset('time')
        for case in self.test_cases:
            case.eval_counts()
            self.set('tests', self.get('tests') + 1)
            if len(case.errors) > 0:
                self.set('errors', self.get('errors') + 1)
            if len(case.failures) > 0:
                self.set('failures', self.get('failures') + 1)
            self.set('skipped', self.get('skipped') + int(case.skipped))
            self.set('time', self.get('time') + case.get('time'))

    def get_digest(self):
        self.eval_counts()
        passed = (self.get('tests') - self.get('failures') - self.get('skipped')
                  - self.get('disabled'))
        return ("{:20} | total= {:5} | (P/F/S)=({:3}/{:3}/{:3})"
                .format(self.get('name'),
               self.get('tests'), passed, self.get('failures'),
               self.get('skipped')))

    def get_digest_grep(self):
        self.eval_counts()
        passed = (self.get('tests') - self.get('failures') - self.get('skipped')
                  - self.get('disabled'))
        values = [str(x) for x in [self.get('name'), self.get('tests'), passed,
                                   self.get('failures'), self.get('skipped')]]
        return " ".join(values)

    def get_xml_element(self, verbose=False):
        self._children = []
        self.eval_counts()
        # the order of these children is strict

        # wrap the properties in a `properties` element for schema reasons
        if len(self.properties) > 0:
            self._children.append(Properties(self.properties))

        self._children.extend(self.test_cases)

        if verbose or len(self.stdout.text) > 0:
            self._children.append(self.stdout)
        if verbose or len(self.stderr.text) > 0:
            self._children.append(self.stderr)

        return super().get_xml_element(verbose)


class TestSuites(Element):
    """The TestSuites element is the root of the Yocto Test results xml
    file. It it's only children are TestSuites.
    """

    TAG = 'testsuites'
    ATTRS = {\
        'disabled': Spec(int, False, 0),
        'errors'  : Spec(int, False, 0),
        'failures': Spec(int, False, 0),
        'name'    : Spec(str, False, ""),
        'tests'   : Spec(int, False, 0),
        'time'    : Spec(int, False, 0),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_suites = []
        self.eval_counts()

    def add_test_suite(self, test_suite):
        self.test_suites.append(test_suite)
        self.eval_counts()

    def eval_counts(self):
        counts = ['tests', 'errors', 'failures', 'time']
        for count in counts:
            self.reset(count)
        for suite in self.test_suites:
            suite.eval_counts()
            for count in counts:
                self.set(count, self.get(count) + suite.get(count))

    def get_digest(self):
        passed = 0
        skipped = 0
        for e_suite in self.test_suites:
            e_suite.eval_counts()
            passed += (e_suite.get('tests') - e_suite.get('failures') -
                       e_suite.get('skipped') - e_suite.get('disabled'))
            skipped += e_suite.get('skipped')
        self.eval_counts()

        return ("{:26} | {:^5} test suites | (P/F/S)=({}/{}/{})"
               .format(self.get('name'), len(self.test_suites),
                       passed, self.get('failures'), skipped))

    def get_digest_grep(self):
        passed = 0
        skipped = 0
        for e_suite in self.test_suites:
            e_suite.eval_counts()
            passed += (e_suite.get('tests') - e_suite.get('failures') -
                       e_suite.get('skipped') - e_suite.get('disabled'))
            skipped += e_suite.get('skipped')
        self.eval_counts()
        return " ".join([self.get('name'), len(self.test_suites), passed,
                         self.get('failures'), skipped])

    def get_xml_element(self, verbose=False):
        self._children = []
        self.eval_counts()

        self._children.extend(self.test_suites)
        return super().get_xml_element(verbose)
