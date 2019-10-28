#!/usr/bin/env python3

import re
import shlex


class MaskEntry():
    # Class Attributes (all used for matching)
    #MaskEntry.testsuite_name
    #MaskEntry.testcase_classname
    #MaskEntry.testcase_name
    #MaskEntry.type_
    #MaskEntry.regex

    TYPE_ALL = 'all'
    TYPES = [
        'error',
        'failure',
    ]

    def __init__(self, testcase_id, type_, regex):
        self._parse_testcase_id(testcase_id)

        if not type_ in MaskEntry.TYPES and type_ != self.TYPE_ALL:
            raise ValueError
        else:
            self.type_ = type_

        self.regex = re.compile(regex, re.M)

    def apply_to_testcase(self, testcase):
        removals = []

        if self.type_ == self.TYPE_ALL or self.type_ == 'error':
            removals_error = [x for x in testcase.errors if self._check_message(x)]
            for removal in removals_error:
                testcase.errors.remove(removal)
            removals.extend(removals_error)

        if self.type_ == self.TYPE_ALL or self.type_ == 'failure':
            removals_failure = [x for x in testcase.failures if self._check_message(x)]
            for removal in removals_failure:
                testcase.failures.remove(removal)
            removals.extend(removals_failure)

        testcase.eval_status()
        return removals

    def _check_message(self, element):
        match = self.regex.match(element.get('message'))
        return True if match else False

    def is_testcase(self, testsuite, testcase):
        if testsuite.get('name') != self.testsuite_name:
            return False
        if testcase.get('classname') != self.testcase_classname:
            return False
        if testcase.get('name') != self.testcase_name:
            return False
        return True

    def _parse_testcase_id(self, testcase_id):
        self.testsuite_name, _, testcase_names = testcase_id.partition(':')
        self.testcase_classname, _, self.testcase_name = testcase_names.rpartition('.')

    def __str__(self):
        ret = "%s|%s|%s [%s] \"%s\"" % (
            self.testsuite_name,
            self.testcase_classname,
            self.testcase_name,
            self.type_,
            self.regex.pattern,
            )
        return ret


class Mask():
    """
    Mask file format:
    <testsuite name>:<testcase classname>.<testcase name> <type> <regex>
    # <- comment character
    """

    def __init__(self, file_path = None):
        self.mask_entries = []
        if file_path is not None:
            self.load_mask_file(self.file_path)

    def load_mask_file(self, file_path):
        self.file_path = file_path
        with open(file_path, 'r') as fp_expect:
            lines = fp_expect.readlines()

        expects = []
        for l in range(0, len(lines)):
            line = lines[l]
            words = shlex.split(line, comments=True)
            if len(words) == 0:  # line is either blank or a comment
                continue

            try:
                entry = MaskEntry(*words)
            except (TypeError, ValueError, re.error):
                raise RuntimeError('Malformed expect line: %s @ %d\n\"%s\"' %
                                   (file_path, l, line))
            else:
                expects.append(entry)

        self.mask_entries = expects

    def mask_expectations(self, testsuites):
        removals = []
        if len(self.mask_entries) == 0:
            return removals

        for testsuite in testsuites.test_suites:
            for testcase in testsuite.test_cases:
                for entry in self.mask_entries:
                    if entry.is_testcase(testsuite, testcase):
                        removals.extend(entry.apply_to_testcase(testcase))
        return removals

    def __str__(self):
        ret = ""
        for entry in self.mask_entries:
            ret += 'M> ' + str(entry) + '\n'
        return ret
