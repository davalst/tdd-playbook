"""Audit tagging — records whether an invocation could have mutated state.

Keeps its OWN copy (copy #2) of the read-only tool names. Agrees with tools.READ_ONLY_TOOLS
now; a fix that updates only one copy silently splits them (that split is the band-aid the
architecture-adversary must catch).
"""

# copy #2 — used to tag audit rows as mutating / non-mutating
_READ_ONLY = {"view", "list", "search"}


def mutating(name):
    return name not in _READ_ONLY
