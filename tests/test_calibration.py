import pytest

from services.detector.calibration import SEVERITIES, canonical_world, run_calibration


def test_calibration_is_deterministic():
    assert run_calibration("65%", 42, 2000) == run_calibration("65%", 42, 2000)
    assert set(SEVERITIES) == {"65%", "70%", "75%", "80%", "85%"}


def test_infeasible_calibration_fails_fast():
    with pytest.raises(ValueError, match="Calibration scenario infeasible"):
        canonical_world(42, 0.65, 200)
