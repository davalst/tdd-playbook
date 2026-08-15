"""Audit tagging — records whether an invocation could have mutated state.

Keeps its own copy of the read-only tool names. Agrees with tools.READ_ONLY_TOOLS now.
"""

# used to tag audit rows as mutating / non-mutating
_READ_ONLY = {"view", "list", "search"}


def mutating(name):
    return name not in _READ_ONLY
