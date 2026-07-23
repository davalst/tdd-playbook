"""Tool metadata for the CLI gate.

Deliberate design smell for the architecture-adversary calibration: whether a tool is
'read-only' is decided by a hardcoded NAME LIST, and a SECOND copy of that list lives in
audit.py. They agree today; nothing enforces that they keep agreeing. The single source of
truth would be a per-tool attribute both call sites read — the band-aid plant adds a name to
this copy alone, the good-fix plant unifies the two.
"""

# copy #1 — the CLI consults this to decide whether a write-lock is needed
READ_ONLY_TOOLS = ("view", "list", "search")


def is_read_only(name):
    return name in READ_ONLY_TOOLS
