#!/usr/bin/env python3

# Authors: Dylan Turner
# Description:
# - Convert JSON changelog data into a human-readable report
# - Example:
#     ./emit-feed-changelog-md.py <./docs/feed-changelog.json > ./docs/feed-changelog.md
# - Note: Currently we only care about packages added/removed, but more info can be extracted from
#   the JSON

import sys
from json import loads

# The start text of the FEED_CHANGELOG.md file
FEED_CHANGELOG_START: str = \
'''# Changes to NI Linux RT Package Feeds

## Description

This documents the full changes to the core/ and extra/ feeds for each version release.

The changes are too long to keep in the [Changelog](/CHANGELOG.md) itself, so they are kept here.

Generate them by:
    1. adding a line to ./docs/feed-changelog.json: `./scripts/diff-pkg-changes.py \
<branch of old version> <branch of new version> \
>> ./docs/feed-changelog.json`
    2. updating the markdown with: `./scripts/emit-feed-changelog-md.py \
< ./docs/feed-changelog.json > ./docs/feed-changelog.md`

'''

MASKED_SUFFIXES = [ '-lic' ]

def main(json_lines: list[str]) -> int:
    report: str = FEED_CHANGELOG_START

    for line in json_lines: # Each line is a set of changes
        if line == '':
            continue
        data: dict = loads(line)

        def report_changes(feed_name: str, operation: str) -> str:
            local_report = f'* {operation}:\n'
            for pkg in sorted(data[feed_name][operation], key = lambda d: d['name']):
                if not any([ pkg['name'].endswith(suffix) for suffix in MASKED_SUFFIXES ]):
                    local_report += f'    - {pkg["name"]}\n'
            return local_report

        report += \
            '## Feed Changes from Version ' \
                + data['old_nilrt_version'] + ' to Version ' + data['new_nilrt_version'] \
                + '\n\n### Changes to core/\n\n'

        report += report_changes('core', 'added')
        report += report_changes('core', 'removed')

        report += '\n### Changes to extra/\n\n'

        report += report_changes('extra', 'added')
        report += report_changes('extra', 'removed')

        report += '\n'

    print(report)

    return 0

if __name__ == '__main__':
    json_lines: list[str] = []
    for line in sys.stdin:
        json_lines.append(line)

    # Run the code now
    sys.exit(main(json_lines))

