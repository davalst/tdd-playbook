"""Fixture CLI — the real user entry point (the wiring the Tripwire cares about)."""
import sys

from calc import apply_discount, authorize
from report import export_csv


def main(argv):
    user = {"role": "admin"}
    if not argv:
        print("usage: cli.py discount PRICE PCT | export")
        return 2
    cmd = argv[0]
    if cmd == "discount":
        if not authorize(user, "discount"):
            print("denied")
            return 1
        print(apply_discount(float(argv[1]), float(argv[2])))
        return 0
    if cmd == "export":
        if not authorize(user, "export"):
            print("denied")
            return 1
        sys.stdout.write(export_csv([("alice", 10), ("bob", 20)]))
        return 0
    print("unknown command: {}".format(cmd))
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
