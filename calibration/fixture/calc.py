"""Known-good fixture module. Deliberately small; the PLANTS provide the challenge."""


def apply_discount(price, pct):
    """Discounted price, rounded to cents. pct must be within [0, 100]."""
    if pct < 0 or pct > 100:
        raise ValueError("pct out of range: {}".format(pct))
    return round(price * (100 - pct) / 100.0, 2)


def authorize(user, action):
    """Admins may do anything; others only what their grants list allows."""
    if user.get("role") == "admin":
        return True
    return action in user.get("grants", ())
