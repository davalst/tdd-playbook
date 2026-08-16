"""The calibration answer-key exclusion (briefs D3, arch-F1/G2).

Every NESTED claude the calibration pipeline spawns must run with deliberation capture
OFF: the doer's turns and — just as critically — the plant-authoring adversary's output
ARE the answer key, and a capture store holding them defeats the planted-error anchor
(the one ungameable calibration signal). This helper is the single source of that child
environment; BOTH spawn sites (run_calibration.run_agent and author_plants.cmd_author)
must build their subprocess env through it — pinned by two-site stub tests in
test_harness.py. The env knob deliberately rides the canonical TDD_PLAYBOOK_HOOK_<NAME>
surface (no new kill-switch vocabulary), and capture.py gives env `off` precedence over
the enrollment marker precisely so this exclusion holds on David's enrolled machine.
"""
import os


def child_env():
    env = dict(os.environ)
    env["TDD_PLAYBOOK_HOOK_CAPTURE"] = "off"
    # The answer-key LOCATION must never reach a nested model (the doer OR the plant-authoring
    # adversary): knowing where the ephemeral clone sits turns any allow-default read into a
    # targeted one (security F2). The sandbox denies the clone tree; stripping these removes even
    # the pointer — defense in depth. The trusted PARENT keeps them (it computes the deny root
    # and loads bodies through os.environ, not this child copy).
    for k in ("TDD_PLAYBOOK_HOLDOUT_DIR", "TDD_PLAYBOOK_HOLDOUT_DENY",
              "TDD_PLAYBOOK_HOLDOUT_REGISTER"):
        env.pop(k, None)
    return env
