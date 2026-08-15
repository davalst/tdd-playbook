"""Tool metadata for the CLI gate.

Whether a tool is read-only is decided by the name list below; audit.py keeps its own
copy of the same list. They agree today.
"""

# copy #1 — the CLI consults this to decide whether a write-lock is needed
READ_ONLY_TOOLS = ("view", "list", "search")


def is_read_only(name):
    return name in READ_ONLY_TOOLS
