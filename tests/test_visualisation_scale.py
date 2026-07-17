from goldilocks_cli.core.visualisation_scale import (
    HARD_NODE_THRESHOLD,
    SOFT_NODE_THRESHOLD,
    choose_collapse,
    combined_view_is_safe,
)


def test_below_soft_threshold_defaults_collapse_off():
    assert choose_collapse(SOFT_NODE_THRESHOLD - 1) is False


def test_at_soft_threshold_defaults_collapse_on():
    assert choose_collapse(SOFT_NODE_THRESHOLD) is True


def test_above_soft_threshold_defaults_collapse_on():
    assert choose_collapse(SOFT_NODE_THRESHOLD + 20) is True


def test_explicit_collapse_overrides_default():
    assert choose_collapse(10, True) is True


def test_explicit_no_collapse_overrides_default():
    assert choose_collapse(100, False) is False


def test_hard_threshold_blocks_combined_mega_rendering():
    assert combined_view_is_safe(HARD_NODE_THRESHOLD - 1) is True
    assert combined_view_is_safe(HARD_NODE_THRESHOLD) is False
