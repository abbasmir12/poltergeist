"""Sanity meter mechanics."""

from poltergeist.ui.sanity import Sanity


def test_success_restores_failure_drains():
    s = Sanity(value=50)
    s.on_command(exit_code=0)
    assert s.value == 53
    s.on_command(exit_code=1)
    assert s.value == 46


def test_bounds():
    s = Sanity(value=99)
    for _ in range(15):
        s.on_command(exit_code=2)
    assert s.value == 0
    s2 = Sanity(value=95)
    for _ in range(5):
        s2.on_command(exit_code=0)
    assert s2.value == 100


def test_levels_thresholds():
    assert Sanity(value=80).level == "steady"
    assert Sanity(value=60).level == "uneasy"
    assert Sanity(value=30).level == "haunted"
    assert Sanity(value=10).level == "crumbling"
    assert Sanity(value=0).level == "meltdown"


def test_bar_shape():
    bar = Sanity(value=50).bar()
    assert bar.startswith("[") and bar.endswith("50%]")
    assert "█" in bar and "░" in bar


def test_repeated_failures_window():
    import time as _t

    s = Sanity()
    s._recent_failures = [int(_t.time()) - 10, int(_t.time()) - 10, int(_t.time()) - 400]
    assert s.repeated_failures(window=300) == 2


def test_drain_idle():
    s = Sanity(value=50)
    s.drain(idle_seconds=600)  # ten idle minutes × 2/min
    assert s.value == 50 - 20
