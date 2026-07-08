"""CSV export for the fixture CLI."""


def export_csv(rows):
    """Rows of (name, amount) -> CSV text with a header line."""
    out = ["name,amount"]
    for name, amount in rows:
        out.append("{},{}".format(name, amount))
    return "\n".join(out) + "\n"
