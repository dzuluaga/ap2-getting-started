import roles


def test_six_roles_are_defined():
    assert len(roles.ROLES) == 6
    assert "Shopping Agent" in roles.ROLES


def test_human_present_signs_a_checkout_mandate():
    steps = roles.human_present_steps()
    assert any("Checkout Mandate" in s for s in steps)


def test_human_not_present_uses_open_then_closed_mandate():
    steps = roles.human_not_present_steps()
    joined = " ".join(steps).lower()
    assert "open" in joined and "closed" in joined
