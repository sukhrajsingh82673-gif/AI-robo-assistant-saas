"""Acceptance Test AT-21: Dataset Calibration Against Reference Agents."""

import pytest
from agent_factory.qa.runner import QARunner


def test_at21_dataset_calibration_known_good_and_bad():
    """AT-21: A dataset may only gate if calibrated against known-good and known-bad agents."""
    runner = QARunner()

    known_good_agent = {
        "metadata": {"name": "calib-good", "category": "finance", "risk_tier": "R1"},
        "role": {"title": "Good Agent"}
    }
    known_bad_agent = {
        "metadata": {"name": "calib-bad", "category": "finance", "risk_tier": "R1"},
        "role": {"title": "Bad Agent"}
    }

    calib_result = runner.calibrate_dataset(
        dataset_name="security-prompt-injection-v1",
        known_good_agent=known_good_agent,
        known_bad_agent=known_bad_agent,
        risk_tier="R1"
    )

    assert calib_result["calibrated"] is True
    assert calib_result["known_good_passed"] is True
    assert calib_result["known_bad_passed"] is False
