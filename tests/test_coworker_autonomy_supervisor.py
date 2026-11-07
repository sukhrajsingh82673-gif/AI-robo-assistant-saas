"""
ZONATA Coworker Autonomy Supervisor — tests.

These tests verify the scheduler contract, not model quality:
* only eligible missions advance;
* human/approval holds are never bypassed;
* KillSwitch holds fail closed;
* the process file lock prevents duplicate schedulers;
* the supervisor is wired into the tenant runtime.
"""

import os
import sys
import time

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.coworker.runtime_supervisor import (
    CoworkerAutonomySupervisor,
    ensure_supervisor,
    shutdown_all_supervisors,
)


class FakeKillswitch:
    def __init__(self, active=False):
        self.active = active
        self.checked = []

    def is_activated(self, level, target_id=None):
        self.checked.append((level, target_id))
        return self.active


class FakeMission:
    def __init__(self, mission_id, status="RUNNING", human_control=False, stage="Working", progress=20.0):
        self.mission_id = mission_id
        self.status = status
        self.human_control = human_control
        self.current_stage = stage
        self.progress_percent = progress
        self.timeline = []


class FakeDispatcher:
    def __init__(self, missions):
        self.missions = {m.mission_id: m for m in missions}
        self.executed = []
        self.retried = []

    def list_missions(self):
        return list(self.missions.values())

    def get_mission(self, mission_id):
        return self.missions.get(mission_id)

    def execute_compound_mission_step(self, mission_id):
        self.executed.append(mission_id)
        mission = self.missions.get(mission_id)
        if mission:
            mission.progress_percent += 5.0
            if mission.status == "PLANNED":
                mission.status = "RUNNING"
        return mission

    def retry_mission(self, mission_id):
        self.retried.append(mission_id)
        mission = self.missions.get(mission_id)
        if mission:
            mission.status = "RUNNING"
        return mission


class FakeLoop:
    def __init__(self, pending=None):
        self.cycles = []
        self.pending = pending or []

    def run_cycle(self, max_items=10):
        self.cycles.append(max_items)
        return []

    def get_pending_approvals(self):
        return list(self.pending)


class FakeEngine:
    def __init__(self, tenant_id="tnt_fake", company_id="comp_fake", killswitch=None, missions=None, pending=None):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.db_path = None
        self.killswitch = killswitch or FakeKillswitch()
        self.background_dispatcher = FakeDispatcher(missions or [])
        self.executive_loop = FakeLoop(pending=pending)
        self.defense_monitor = None


@pytest.fixture(autouse=True)
def cleanup_supervisors():
    yield
    shutdown_all_supervisors(timeout=2.0)


def test_autonomy_disabled_by_default_under_test_mode(monkeypatch):
    monkeypatch.delenv("ZONATA_COWORKER_AUTONOMY", raising=False)
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    engine = FakeEngine()

    supervisor = CoworkerAutonomySupervisor(engine, enable_patrol=False, acquire_process_lock=False)

    assert supervisor.enabled is False
    assert supervisor.status()["mode"] == "DISABLED"
    # A disabled supervisor must not start unless a human explicitly starts it.
    supervisor.start()
    assert supervisor.is_running() is False


def test_tick_advances_only_eligible_missions_and_holds_approvals():
    missions = [
        FakeMission("m_running", "RUNNING"),
        FakeMission("m_planned", "PLANNED"),
        FakeMission("m_waiting", "WAITING"),
        FakeMission("m_approval", "AWAITING_APPROVAL"),
        FakeMission("m_blocked", "BLOCKED", stage="BLOCKED — no language model provider is available"),
        FakeMission("m_done", "COMPLETED"),
        FakeMission("m_human", "RUNNING", human_control=True),
    ]
    engine = FakeEngine(missions=missions, pending=[object()])
    supervisor = CoworkerAutonomySupervisor(
        engine,
        enable_patrol=False,
        acquire_process_lock=False,
        retry_blocked=False,
        mission_cooldown_sec=0.0,
    )

    result = supervisor.run_once(trigger="test")

    assert result["status"] == "OK"
    assert result["missions_advanced"] == 2
    assert engine.background_dispatcher.executed == ["m_running", "m_planned"]
    assert result["missions_held"] == 3  # WAITING + AWAITING_APPROVAL + human_control
    assert result["approvals_auto_approved"] == 0
    assert len(result["approvals_pending"]) == 3  # DoA item + WAITING + AWAITING_APPROVAL
    assert engine.executive_loop.cycles == [10]
    # The approval queue is never mutated by the scheduler.
    assert len(engine.executive_loop.get_pending_approvals()) == 1


def test_work_item_below_doa_is_queued_for_the_next_tick():
    from core.coworker.ceo_coworker_bridge import AICeoMissionRequest
    from core.coworker.executive_operating_loop import ExecutiveOperatingLoop

    loop = ExecutiveOperatingLoop(bridge=object(), doa_ceiling_usd=10.0, tenant_id="tnt_fake")
    request = AICeoMissionRequest(objective="small governed job", budget=5.0, tenant_id="tnt_fake")
    item = loop.submit_work_item(
        "Small job", "Within DoA", cost_estimate_usd=1.0, mission_request=request
    )

    assert item.status.value == "PENDING"
    assert item.requires_human_approval is False
    assert loop.get_queue_depth() == 1
    assert item.mission_request is request


def test_bootstrap_is_skipped_in_test_mode(monkeypatch):
    from core.coworker.runtime_supervisor import bootstrap_tenant_supervisors

    monkeypatch.delenv("ZONATA_COWORKER_AUTONOMY", raising=False)
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    assert bootstrap_tenant_supervisors(limit=1, delay=0.0) == 0


def test_doa_work_item_is_surfaced_but_never_auto_approved():
    from core.coworker.executive_operating_loop import ExecutiveOperatingLoop

    engine = FakeEngine()
    loop = ExecutiveOperatingLoop(bridge=object(), doa_ceiling_usd=10.0, tenant_id="tnt_fake")
    item = loop.submit_work_item("Large purchase", "Exceeds DoA", cost_estimate_usd=100.0)
    engine.executive_loop = loop
    supervisor = CoworkerAutonomySupervisor(engine, enable_patrol=False, acquire_process_lock=False)

    result = supervisor.run_once(trigger="test")

    assert item.status.value == "AWAITING_APPROVAL"
    assert any(a.get("type") == "DOA_APPROVAL" and a.get("item_id") == item.item_id
               for a in result["approvals_pending"])
    assert result["approvals_auto_approved"] == 0
    assert loop.get_pending_approvals() == [item]

    # Only an explicit human approval moves it.
    assert loop.approve_work_item(item.item_id, approver_role="OWNER") is True
    assert item.status.value == "PENDING"
    assert loop.get_pending_approvals() == []


def test_killswitch_holds_every_engine_fail_closed():
    engine = FakeEngine(killswitch=FakeKillswitch(active=True), missions=[FakeMission("m1", "RUNNING")])
    supervisor = CoworkerAutonomySupervisor(engine, enable_patrol=False, acquire_process_lock=False)

    result = supervisor.run_once(trigger="test")

    assert result["status"] == "KILLSWITCH_HOLD"
    assert result["killswitch"]["active"] is True
    assert engine.background_dispatcher.executed == []
    assert engine.executive_loop.cycles == []
    assert supervisor.status()["mode"] == "KILLSWITCH_HOLD"


def test_missing_killswitch_fails_closed():
    engine = FakeEngine(missions=[FakeMission("m1", "RUNNING")])
    engine.killswitch = None
    supervisor = CoworkerAutonomySupervisor(engine, enable_patrol=False, acquire_process_lock=False)

    result = supervisor.run_once(trigger="test")

    assert result["status"] == "KILLSWITCH_HOLD"
    assert result["killswitch"]["error"] == "KILLSWITCH_UNAVAILABLE"
    assert engine.background_dispatcher.executed == []


def test_background_scheduler_starts_ticks_and_stops():
    engine = FakeEngine(missions=[FakeMission("m1", "RUNNING")])
    supervisor = CoworkerAutonomySupervisor(
        engine,
        tick_interval_sec=0.05,
        enable_patrol=False,
        acquire_process_lock=False,
        mission_cooldown_sec=0.0,
    )

    supervisor.start(manual=True)
    assert supervisor.is_running() is True

    deadline = time.time() + 2.0
    while supervisor.status()["counters"]["ticks"] < 1 and time.time() < deadline:
        time.sleep(0.02)
    assert supervisor.status()["counters"]["ticks"] >= 1

    status = supervisor.stop(timeout=2.0)
    assert status["running"] is False
    assert status["thread_alive"] is False
    assert engine.background_dispatcher.executed


def test_process_lock_rejects_a_second_scheduler():
    engine_a = FakeEngine(tenant_id="tnt_lock", company_id="comp_lock", missions=[FakeMission("m1", "RUNNING")])
    engine_b = FakeEngine(tenant_id="tnt_lock", company_id="comp_lock", missions=[FakeMission("m1", "RUNNING")])

    first = CoworkerAutonomySupervisor(engine_a, enable_patrol=False, acquire_process_lock=True)
    second = CoworkerAutonomySupervisor(engine_b, enable_patrol=False, acquire_process_lock=True)

    first_status = first.start(manual=True)
    second_status = second.start(manual=True)
    try:
        assert first_status["running"] is True
        assert second_status["running"] is False
        assert second_status["mode"] == "STANDBY"
        assert second_status["process_lock"]["acquired"] is False
    finally:
        first.stop(timeout=2.0)


def test_ensure_supervisor_autostarts_when_enabled(monkeypatch):
    monkeypatch.setenv("ZONATA_COWORKER_AUTONOMY", "1")
    engine = FakeEngine(tenant_id="tnt_autostart", missions=[FakeMission("m1", "RUNNING")])

    supervisor = ensure_supervisor(engine)
    try:
        assert supervisor.enabled is True
        assert supervisor.is_running() is True
        assert ensure_supervisor(engine) is supervisor
    finally:
        supervisor.stop(timeout=2.0)


def test_tenant_runtime_wires_supervisor_without_starting_in_test_mode(monkeypatch):
    monkeypatch.delenv("ZONATA_COWORKER_AUTONOMY", raising=False)
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    from core.tenancy import get_runtime, invalidate

    tenant_id = f"tnt_autonomy_wire_{int(time.time() * 1000)}"
    runtime = get_runtime(tenant_id, "comp_wire")
    try:
        engine = runtime.coworker
        assert engine.autonomy_supervisor is not None
        assert engine.autonomy_supervisor.status()["mode"] == "DISABLED"
        assert engine.execute_task is not None
    finally:
        invalidate(tenant_id)


def test_real_dispatcher_holds_mission_when_killswitch_engaged():
    from core.coworker.engine import UniversalCoworkerEngine
    from core.killswitch_matrix import KillSwitchLevel

    tenant_id = f"tnt_autonomy_ks_{int(time.time() * 1000)}"
    engine = UniversalCoworkerEngine(tenant_id=tenant_id)
    switch_id = engine.killswitch.activate(
        KillSwitchLevel.TENANT, tenant_id, "autonomy test hold"
    )
    try:
        mission = engine.background_dispatcher.submit_background_prompt(
            "prepare a governed test deliverable", initiator="test"
        )
        assert mission.status == "RUNNING"
        progress_before = mission.progress_percent

        stepped = engine.background_dispatcher.execute_compound_mission_step(mission.mission_id)

        assert stepped.status == "RUNNING"
        assert stepped.progress_percent == progress_before
        assert any(e.get("stage") == "KILLSWITCH_HOLD" for e in stepped.timeline)
    finally:
        engine.killswitch.deactivate(KillSwitchLevel.TENANT, tenant_id)

    # After disengagement the gate clears and progression is allowed again.
    assert engine.killswitch.is_activated(KillSwitchLevel.TENANT, tenant_id) is False
