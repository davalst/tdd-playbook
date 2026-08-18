#!/usr/bin/env python3
"""readable_surface — what the system IS, organised by worry, for the reader who cannot
fall back to source (v1.34.0 D3; plan: docs/plans/gated/2026-08-12-readable-surface.md).

Every Playbook output before this one is a VERDICT (N/N, green/red). This is the first
whose output is DESCRIPTION: mechanical facts composed from producers that ALREADY exist —
capabilities.json (nodes), dataflow-sweeps.json (edges), gate-manifest.json (suites),
docs/architecture/host-parity.json (surfaces) — grouped by the QUESTION they answer, never
by the code's own layout (the organisation the reader cannot navigate). Not an extractor:
any new derivation belongs to the existing owner.

The surface is POINTABLE, not complete: every row cites file:line so "explain this one" is
a well-scoped agent dispatch, and an omission is recoverable where a wrong statement is
not. Stdout only — no committed artifact, no staleness gate (those only pay off if the
surface is read repeatedly, which is what v1.34.0 measures; see docs/calibration/usage.md).

    readable_surface.py facts          # all worry pages
    readable_surface.py facts S17      # one scenario, via the inventory's Facts column

Exit contract: 0 rendered · 2 usage · 3 vacuous-refusal (the dataflow_sweeps constant —
an empty registry must never render an empty page that reads as "nothing here"; run
`capability_registry.py init` first). An absent fact renders "not stated" — an absent fact
and a false fact must look different. Two runs on an unchanged tree are byte-identical.
Each `facts` run logs ONE machine usage event through hooks/scripts/_common.log_yield_event
(the single write path; host-stamped, never suppressed) — the denominator of the
keep/kill record. Stdlib-only.
"""
import argparse
import json
import os
import re
import sys

_BIN = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BIN)
import dataflow_sweeps as _ds  # noqa: E402  (sibling, vendored alongside)

EXIT_CLEAN, EXIT_USAGE, EXIT_VACUOUS = 0, 2, _ds.EXIT_VACUOUS

# ---------------------------------------------------------------- owned vocabularies
# The failure-class vocabulary (§6c T1–T7 + the integration-audit darkness classes).
# ONE machine owner (arch-adversary F6: T1–T7 existed only as prose in SKILL/commands,
# enforced by string presence — a rename would leave every copy silently wrong). The
# inventory's Class column and its test import THIS tuple; SKILL §6c is pinned against
# the T-members by test_readable_surface.py.
CLASSES = ("T1", "T2", "T3", "T4", "T5", "T6", "T7",
           "broken-wiring", "dark-by-default", "surface-drift", "old-blind-to-new",
           "write-only", "vacuity", "seam", "flaky", "new")

# The worry pages: (page_id, the question it answers, scenario IDs it answers).
# The inventory's Facts column is pinned to THIS declaration in both directions — one
# derivation, never two hand-maintained sides of a join (arch-adversary F7). A page that
# answers no scenario is REPORTED by the test, not hidden.
PAGES = (
    ("activation", "What is ON, OFF-with-a-switch, or dark — and can a user reach it?",
     ("S36", "S38")),
    ("guards", "What blocks, what warns, what was retired to off?",
     ("S24",)),
    ("dark-inventory", "What is built that nothing may be reaching — and is it alive?",
     ("S08", "S32", "S41")),
    ("flows", "What feeds what — and which edges are declared but unarmed?",
     ("S15", "S33")),
    ("debts", "What dated obligations exist, and when does each bite?",
     ()),
    ("test-surface", "What does the gate actually run?",
     ("S14", "S31")),
    ("surfaces", "Which host gets which capability — where is the unguarded twin door?",
     ("S18",)),
)

SUMMARY_RX = (r"readable_surface facts: subsystems (?P<subsystems>\d+) · "
              r"effects (?P<effects>\d+) · unproven (?P<unproven>\d+) · "
              r"not-stated (?P<notstated>\d+)")

NOT_STATED = "not stated"


def project_root():
    return os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _find(root, *cands):
    for rel in cands:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            return p, rel
    return None, None


def _line_of(path, needle):
    """1-based line of the first occurrence — the citation an agent can be pointed at."""
    try:
        with open(path, encoding="utf-8") as fh:
            for i, ln in enumerate(fh, 1):
                if needle in ln:
                    return i
    except OSError:
        pass
    return 1


# ---------------------------------------------------------------- inventory parsing
_ROW_RX = re.compile(r"^\|\s*(S\d{2})\s*\|(.+)$")


def parse_inventory(path):
    """Rows of {id, question, role, evidence, route, class, facts} from the standing
    inventory's tables. ONE parser — the resolver test imports this, never a second."""
    rows = []
    if not os.path.isfile(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            m = _ROW_RX.match(ln.strip())
            if not m:
                continue
            cells = [c.strip() for c in m.group(2).strip().strip("|").split("|")]
            if len(cells) != 6:
                continue
            rows.append({"id": m.group(1), "question": cells[0], "role": cells[1],
                         "evidence": cells[2], "route": cells[3], "class": cells[4],
                         "facts": cells[5]})
    return rows


# ---------------------------------------------------------------- fact derivation
def derive(root):
    """Compose the existing producers into per-page fact rows. Returns
    (pages: {page_id: [row-str]}, counts) — deterministic ordering, no timestamps."""
    reg_path, reg_rel = _find(root, "capabilities.json",
                              os.path.join(".claude", "capabilities.json"))
    if not reg_path:
        raise LookupError(
            "no capabilities.json here — the surface would render an empty page that "
            "reads as 'nothing here'. Run `capability_registry.py init` first.")
    with open(reg_path, encoding="utf-8") as fh:
        registry = json.load(fh)
    caps = registry.get("capabilities") or []
    if not caps:
        raise LookupError(
            "capabilities.json has zero entries — refusing a vacuous render. Run "
            "`capability_registry.py init` and register the real subsystems first.")

    pages = {pid: [] for pid, _q, _s in PAGES}
    not_stated = 0
    unproven = 0
    effects = 0

    def cite(rel, needle):
        return "{}:{}".format(rel, _line_of(os.path.join(root, rel), needle))

    for cap in sorted(caps, key=lambda c: str(c.get("id"))):
        cid = str(cap.get("id"))
        c8 = cite(reg_rel, '"{}"'.format(cid))
        act = cap.get("activation")
        if not isinstance(act, dict) or "default" not in act:
            pages["activation"].append(
                "- `{}` — activation {} — {}".format(cid, NOT_STATED, c8))
            not_stated += 1
        elif act.get("default") == "off":
            sw = act.get("switch") or NOT_STATED
            if sw == NOT_STATED:
                not_stated += 1
            pages["activation"].append(
                "- `{}` — OFF; switch: {} — {}".format(cid, sw, c8))
        else:
            pages["activation"].append("- `{}` — on — {}".format(cid, c8))
        emits = cap.get("emits")
        if emits is None:
            pages["dark-inventory"].append(
                "- `{}` — emits {} — {}".format(cid, NOT_STATED, c8))
            not_stated += 1
        else:
            for em in emits:
                effects += 1
                consumers = em.get("consumers") or []
                if not consumers:
                    unproven += 1
                    pages["dark-inventory"].append(
                        "- `{}` emits `{}` and NOTHING reads it — {}".format(
                            cid, em.get("topic"), c8))
                else:
                    pages["flows"].append(
                        "- `{}` → `{}` → {} consumer(s) — {}".format(
                            cid, em.get("topic"), len(consumers), c8))
        live = cap.get("liveness")
        if isinstance(live, dict):
            if not live.get("probe"):
                unproven += 1
                pages["dark-inventory"].append(
                    "- `{}` — liveness declared but NO probe — {}".format(cid, c8))
        for debt in (cap.get("integration_debt") or []):
            what = str(debt.get("what", ""))[:90]
            pages["debts"].append(
                "- `{}` — {}… expires {} — {}".format(
                    cid, what, debt.get("expires", NOT_STATED), c8))

    # edges config: which standing sweeps exist, and which are declared-unarmed
    ds_path, ds_rel = _find(root, "dataflow-sweeps.json")
    if ds_path:
        with open(ds_path, encoding="utf-8") as fh:
            cfg = json.load(fh)
        for name in sorted(cfg.get("unarmed") or []):
            pages["flows"].append(
                "- sweep `{}` — declared UNARMED (a blind spot with an approved shape) "
                "— {}".format(name, cite(ds_rel, name)))
        for name in sorted(k for k in cfg if k not in ("unarmed", "_comment")):
            pages["flows"].append(
                "- sweep `{}` — configured — {}".format(name, cite(ds_rel, name)))
    else:
        pages["flows"].append("- dataflow sweep config: {}".format(NOT_STATED))
        not_stated += 1

    gm_path, gm_rel = _find(root, "gate-manifest.json")
    if gm_path:
        with open(gm_path, encoding="utf-8") as fh:
            gm = json.load(fh)
        import glob as _glob
        suites = sorted(os.path.relpath(p, root)
                        for p in _glob.glob(os.path.join(root, gm["suite_glob"])))
        pages["test-surface"].append(
            "- {} discovered suites + {} fixed stages — {}".format(
                len(suites), len(gm.get("fixed_stages") or []),
                cite(gm_rel, "suite_glob")))
        for s in suites:
            pages["test-surface"].append("- suite `{}` — {}:1".format(
                os.path.basename(s)[:-3], s.replace(os.sep, "/")))
    else:
        pages["test-surface"].append("- gate manifest: {}".format(NOT_STATED))
        not_stated += 1

    hp_path, hp_rel = _find(root, os.path.join("docs", "architecture",
                                               "host-parity.json"))
    if hp_path:
        with open(hp_path, encoding="utf-8") as fh:
            parity = json.load(fh)
        tally = {}
        for family, assets in sorted((parity.get("assets") or {}).items()):
            for asset, hosts in sorted(assets.items()):
                for host, row in sorted(hosts.items()):
                    tally.setdefault(host, {}).setdefault(row.get("status"), 0)
                    tally[host][row.get("status")] += 1
                statuses = {h: r.get("status") for h, r in hosts.items()}
                if len(set(statuses.values())) > 1:
                    pages["surfaces"].append(
                        "- `{}/{}` differs per host: {} — {}".format(
                            family, asset,
                            ", ".join("{}={}".format(h, s)
                                      for h, s in sorted(statuses.items())),
                            cite(hp_rel, '"{}"'.format(asset))))
        for host in sorted(tally):
            pages["surfaces"].insert(0, "- {}: {} — {}:1".format(
                host, ", ".join("{} {}".format(v, k)
                                for k, v in sorted(tally[host].items())), hp_rel))
    else:
        pages["surfaces"].append("- host parity manifest: {}".format(NOT_STATED))
        not_stated += 1

    # guard defaults — owned by hooks/scripts/_common.py; imported, never re-typed
    sys.path.insert(0, os.path.join(_BIN, "..", "hooks", "scripts"))
    try:
        import _common as _hooks_common
        rel = "plugins/tdd-playbook/hooks/scripts/_common.py"
        rel_path = os.path.join(root, rel)
        cite_rel = rel if os.path.isfile(rel_path) else None
        for name, mode in sorted(_hooks_common._DEFAULT_MODES.items()):
            row = "- guard `{}` — default {}".format(name, mode)
            if cite_rel:
                row += " — {}:{}".format(cite_rel,
                                              _line_of(rel_path, '"{}"'.format(name)))
            pages["guards"].append(row)
    except Exception:
        pages["guards"].append("- guard defaults: {}".format(NOT_STATED))
        not_stated += 1

    counts = {"subsystems": len(caps), "effects": effects, "unproven": unproven,
              "notstated": not_stated}
    return pages, counts


def _log_usage(scenario, rows_surfaced):
    """ONE machine event per facts run through the single write path (host-stamped there;
    never suppressed — an unclassified context is labelled, not dropped). Telemetry
    failure never breaks the render, but it is SAID, not swallowed."""
    sys.path.insert(0, os.path.join(_BIN, "..", "hooks", "scripts"))
    try:
        from _common import log_yield_event
    except Exception as exc:
        sys.stderr.write("readable_surface: usage NOT recorded (_common unreachable: "
                         "{})\n".format(exc))
        return
    log_yield_event("readable-surface", "usage",
                    {"scenario": scenario, "rows_surfaced": rows_surfaced},
                    source="cli")


def cmd_facts(args):
    root = project_root()
    try:
        pages, counts = derive(root)
    except LookupError as exc:
        sys.stderr.write("readable_surface: VACUOUS REFUSAL — {}\n".format(exc))
        return EXIT_VACUOUS

    inventory = parse_inventory(os.path.join(root, "docs",
                                             "adversary-scenario-inventory.md"))
    by_id = {r["id"]: r for r in inventory}

    selected = [p for p in PAGES]
    scenario = "full"
    if args.scenario:
        scenario = args.scenario.upper()
        row = by_id.get(scenario)
        if not inventory:
            print("(scenario lookup unavailable: docs/adversary-scenario-inventory.md "
                  "is absent in this repo — rendering all pages instead)")
        elif row is None:
            sys.stderr.write("readable_surface: unknown scenario {} — the inventory "
                             "holds S01..S{:02d}\n".format(scenario, len(inventory)))
            return EXIT_USAGE
        else:
            print("## {} — {}".format(scenario, row["question"]))
            if row["facts"] == "—":
                print("no mechanical facts for this one — it needs judgment: dispatch "
                      "`{}`.".format(row["route"]) if row["route"] != "—" else
                      "no mechanical facts for this one, and no route is armed — see "
                      "the inventory row.")
                _log_usage(scenario, 0)
                return EXIT_CLEAN
            wanted = set(row["facts"].split("+"))
            selected = [p for p in PAGES if p[0] in wanted]
            print()

    surfaced = 0
    for pid, question, _sids in selected:
        rows = pages.get(pid) or []
        print("## {} — {}".format(pid, question))
        if rows:
            for r in rows:
                print(r)
            surfaced += len(rows)
        else:
            print("(nothing derived for this page — an EMPTY page is stated, "
                  "never omitted)")
        print()
    print("readable_surface facts: subsystems {subsystems} · effects {effects} "
          "· unproven {unproven} · not-stated {notstated}".format(**counts))
    _log_usage(scenario, surfaced)
    return EXIT_CLEAN


def main(argv=None):
    ap = argparse.ArgumentParser(description="The readable surface: description, not a "
                                             "verdict. Prose never gates.")
    ap.add_argument("command", choices=["facts"])
    ap.add_argument("scenario", nargs="?", default=None,
                    help="an inventory row (S17) to answer for the current tree")
    args = ap.parse_args(argv)
    return cmd_facts(args)


if __name__ == "__main__":
    sys.exit(main())