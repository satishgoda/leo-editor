#!/usr/bin/env python

# Should be moved to leo-editor/.git/hooks/pre-commit.py
print('===== pre-commit')
import leo.core.leoVersion as v
v.create_commit_timestamp_json(after=True)
