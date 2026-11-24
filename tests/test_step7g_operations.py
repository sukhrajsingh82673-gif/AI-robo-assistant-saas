"""
Unit & Contract Tests for Step 7G: Operations & Production Depth.
================================================================
"""

import pytest
from core.operations.bom import BOMNode, BOMExplosionEngine
from core.operations.work_orders import WorkOrder, WorkOrderManager, WorkOrderOperation
from core.operations.oee import OEECalculator
from core.operations.quality import QualityControlManager
from core.operations.maintenance import MaintenanceReliabilityManager, BreakdownEvent


# --- 1. MULTI-LEVEL BOM EXPLOSION TESTS ---

def test_01_multi_level_bom_explosion_and_shortages():
    # Construct 3-level BOM: Robot -> Arm Assembly -> Motor & Gear
    motor = BOMNode(item_id="COMP-MOTOR", description="Servo Motor", quantity_per_parent=2.0, lead_time_days=5)
    gear = BOMNode(item_id="COMP-GEAR", description="Precision Gear", quantity_per_parent=4.0, lead_time_days=3)
    arm = BOMNode(
        item_id="ASSY-ARM",
        description="Robotic Arm Assembly",
        quantity_per_parent=2.0,
        lead_time_days=2,
        is_assembly=True,
        children=[motor, gear]
    )
    chassis = BOMNode(item_id="COMP-CHASSIS", description="Alloy Chassis", quantity_per_parent=1.0, lead_time_days=4)
    robot = BOMNode(
        item_id="PROD-ROBOT",
        description="Industrial Robot",
        quantity_per_parent=1.0,
        lead_time_days=1,
        is_assembly=True,
        children=[arm, chassis]
    )

    # Inventory balances: motor is short (needs 10 robots * 2 arms * 2 motors = 40 motors, only 15 available)
    inventory = {
        "ASSY-ARM": 0.0,
        "COMP-MOTOR": 15.0,  # Shortage of 25
        "COMP-GEAR": 100.0,
        "COMP-CHASSIS": 20.0
    }

    engine = BOMExplosionEngine()
    result = engine.explode(robot, target_quantity=10.0, inventory_balances=inventory)

    assert result.parent_item_id == "PROD-ROBOT"
    assert result.has_shortages is True
    assert "COMP-MOTOR" in result.shortage_items
    assert "COMP-GEAR" not in result.shortage_items

    # Critical path lead time rollup:
    # robot (1d) + arm (2d) + motor (5d) = 8 days
    assert result.total_lead_time_days == 8


# --- 2. WORK ORDER LIFECYCLE TESTS ---

def test_02_work_order_lifecycle_and_scrap():
    mgr = WorkOrderManager()
    wo = WorkOrder(
        work_order_id="WO-501",
        tenant_id="t1",
        company_id="c1",
        product_id="PROD-ROBOT",
        planned_quantity=10.0,
        operations=[
            WorkOrderOperation(operation_id="OP-1", operation_name="Chassis Milling", workstation_id="CNC-01", planned_hours=5.0)
        ]
    )
    mgr.create_work_order(wo)

    # Cannot start directly from draft
    with pytest.raises(RuntimeError):
        mgr.start_work_order("t1", "c1", "WO-501")

    # Release then start
    mgr.release_work_order("t1", "c1", "WO-501")
    started = mgr.start_work_order("t1", "c1", "WO-501")
    assert started.status == "in_progress"

    # Record output: 9 good units, 1 scrap unit
    completed = mgr.record_production_output("t1", "c1", "WO-501", good_qty=9.0, scrapped_qty=1.0)
    assert completed.status == "completed"
    assert completed.completed_quantity == 9.0
    assert completed.scrapped_quantity == 1.0

    scrap_rate = mgr.calculate_scrap_rate(completed)
    assert scrap_rate == 0.10  # 10% scrap rate


# --- 3. OVERALL EQUIPMENT EFFECTIVENESS (OEE) TESTS ---

def test_03_oee_and_yield_calculation():
    # Shift: 480 mins (8 hours)
    # Planned downtime (breaks, shift change): 60 mins -> Planned production = 420 mins
    # Unplanned downtime (breakdown, jam): 42 mins -> Operating time = 378 mins
    # Availability = 378 / 420 = 0.90 (90%)
    # Total units produced: 360 units. Ideal cycle time: 1.0 min (60 seconds)
    # Ideal operating minutes = 360 * 1.0 = 360 mins.
    # Performance = 360 / 378 = 0.9524 (95.24%)
    # Defective units: 18 units -> Good units = 342.
    # Quality = 342 / 360 = 0.95 (95.0%)
    # OEE = 0.90 * 0.9524 * 0.95 = 0.8143 (81.43%)
    oee = OEECalculator.calculate_oee(
        workstation_id="CNC-01",
        shift_date="2026-10-24",
        scheduled_minutes=480.0,
        planned_downtime_minutes=60.0,
        unplanned_downtime_minutes=42.0,
        ideal_cycle_time_seconds=60.0,
        total_units_produced=360,
        defective_units=18
    )

    assert oee.availability == 0.90
    assert oee.performance == 0.9524
    assert oee.quality == 0.95
    assert oee.oee == 0.8143


# --- 4. QUALITY CONTROL & QUARANTINE GATE TESTS ---

def test_04_quality_control_quarantine_gate():
    qc = QualityControlManager()

    # Case 1: Passing lot (2 defects <= AQL limit of 3)
    pass_lot = qc.record_inspection_result(
        lot_id="LOT-001",
        tenant_id="t1",
        company_id="c1",
        item_id="COMP-GEAR",
        batch_number="BATCH-99A",
        lot_size=1000,
        sample_size=80,
        defect_count=2,
        aql_max_defects=3
    )
    assert pass_lot.status == "approved"
    assert pass_lot.is_quarantined is False
    can_use, _ = qc.can_dispatch_or_consume("t1", "c1", "LOT-001")
    assert can_use is True

    # Case 2: Failed lot (5 defects > AQL limit of 3) -> QUARANTINE
    fail_lot = qc.record_inspection_result(
        lot_id="LOT-002",
        tenant_id="t1",
        company_id="c1",
        item_id="COMP-GEAR",
        batch_number="BATCH-99B",
        lot_size=1000,
        sample_size=80,
        defect_count=5,
        aql_max_defects=3
    )
    assert fail_lot.status == "quarantined"
    assert fail_lot.is_quarantined is True

    # Strict Quarantine Gate: Must reject dispatch or consumption
    can_use_fail, block_reason = qc.can_dispatch_or_consume("t1", "c1", "LOT-002")
    assert can_use_fail is False
    assert "Quarantine Lock" in block_reason


# --- 5. MAINTENANCE & RELIABILITY (MTBF / MTTR) TESTS ---

def test_05_maintenance_mtbf_mttr_metrics():
    breakdowns = [
        BreakdownEvent(
            event_id="BD-1",
            workstation_id="ROBOT-CELL-1",
            occurred_at="2026-10-01T08:00:00",
            repair_started_at="2026-10-01T08:15:00",
            repair_completed_at="2026-10-01T10:15:00",
            downtime_hours=2.0,
            failure_cause="Hydraulic Seal Leak"
        ),
        BreakdownEvent(
            event_id="BD-2",
            workstation_id="ROBOT-CELL-1",
            occurred_at="2026-10-15T14:00:00",
            repair_started_at="2026-10-15T14:30:00",
            repair_completed_at="2026-10-15T18:30:00",
            downtime_hours=4.0,
            failure_cause="Servo Motor Overheating"
        ),
    ]

    # Total operating hours: 500 hours
    # Failures: 2
    # MTBF = 500 / 2 = 250.0 hours
    # Total repair hours: 2 + 4 = 6.0 hours
    # MTTR = 6.0 / 2 = 3.0 hours
    rel = MaintenanceReliabilityManager.calculate_reliability("ROBOT-CELL-1", 500.0, breakdowns)
    assert rel.failure_count == 2
    assert rel.mtbf_hours == 250.0
    assert rel.mttr_hours == 3.0
    assert rel.availability_ratio == round(500.0 / 506.0, 4)
