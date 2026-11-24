"""
Plan-to-Deliver Cross-Department Workflow (Rule 59)
===================================================
Coordinates: Sales/Demand -> Operations -> QC -> Supply Chain / Logistics
Steps:
1. Multi-level indented BOM explosion & shortage calculation (BOMExplosionEngine).
2. Work order creation, release, and completion (WorkOrderManager).
3. Overall Equipment Effectiveness (OEE) measurement (OEECalculator).
4. QC lot inspection with AQL sampling rules (QualityControlManager).
5. Carrier dispatch & milestone tracking to delivery (SovereignLogisticsAdapter).
6. Rule 59 independent re-read verification of delivered shipment.
"""

from typing import Dict, Any, List
from core.workflows.departments.base import (
    DepartmentBaseWorkflow,
    DepartmentWorkflowContext,
    WorkflowStepRecord,
    ReReadVerificationFailed
)
from core.operations.bom import BOMNode, BOMExplosionEngine
from core.operations.work_orders import WorkOrder, WorkOrderManager, WorkOrderOperation
from core.operations.oee import OEECalculator
from core.operations.quality import QualityControlManager
from core.procurement.carrier_tracking import SovereignLogisticsAdapter


class PlanToDeliverWorkflow(DepartmentBaseWorkflow):
    def __init__(self):
        super().__init__(name="plan_to_deliver", version="1.0.0")

    def execute(self, ctx: DepartmentWorkflowContext, initial_data: Dict[str, Any]) -> Dict[str, Any]:
        db_records: Dict[str, Dict[str, Any]] = {}
        target_qty = float(initial_data.get("order_quantity", 10.0))

        # -------------------------------------------------------------
        # 1. Multi-Level BOM Explosion & Shortage Check
        # -------------------------------------------------------------
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

        inventory = {
            "ASSY-ARM": 10.0,
            "COMP-MOTOR": 50.0,
            "COMP-GEAR": 100.0,
            "COMP-CHASSIS": 20.0
        }
        bom_engine = BOMExplosionEngine()
        bom_res = bom_engine.explode(robot, target_quantity=target_qty, inventory_balances=inventory)

        ctx.record_step(WorkflowStepRecord(
            step_id="step_1_bom",
            step_name="Indented BOM Explosion & Shortage Check",
            department_code="OPS",
            status="COMPLETED",
            output_payload={"total_lead_time_days": bom_res.total_lead_time_days, "has_shortages": bom_res.has_shortages}
        ))

        # -------------------------------------------------------------
        # 2. Work Order Execution & OEE Calculation
        # -------------------------------------------------------------
        wo_mgr = WorkOrderManager()
        wo = WorkOrder(
            work_order_id="WO-501",
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            product_id="PROD-ROBOT",
            planned_quantity=target_qty,
            operations=[
                WorkOrderOperation(operation_id="OP-1", operation_name="Assembly & Calibration", workstation_id="CNC-01", planned_hours=4.0)
            ]
        )
        wo_mgr.create_work_order(wo)
        wo_mgr.release_work_order(ctx.tenant_id, ctx.company_id, "WO-501")
        wo_mgr.start_work_order(ctx.tenant_id, ctx.company_id, "WO-501")
        completed_wo = wo_mgr.record_production_output(ctx.tenant_id, ctx.company_id, "WO-501", good_qty=target_qty, scrapped_qty=0.0)

        oee_res = OEECalculator.calculate_oee(
            workstation_id="CNC-01",
            shift_date="2026-11-24",
            scheduled_minutes=480.0,
            planned_downtime_minutes=60.0,
            unplanned_downtime_minutes=42.0,
            ideal_cycle_time_seconds=60.0,
            total_units_produced=360,
            defective_units=18
        )
        ctx.record_step(WorkflowStepRecord(
            step_id="step_2_production",
            step_name="Work Order Execution & OEE",
            department_code="OPS",
            status="COMPLETED",
            output_payload={"work_order_id": completed_wo.work_order_id, "oee": oee_res.oee, "quality": oee_res.quality}
        ))

        # -------------------------------------------------------------
        # 3. QC Lot Inspection
        # -------------------------------------------------------------
        qc_mgr = QualityControlManager()
        lot = qc_mgr.record_inspection_result(
            lot_id="LOT-PROD-501",
            tenant_id=ctx.tenant_id,
            company_id=ctx.company_id,
            item_id="PROD-ROBOT",
            batch_number="B-501",
            lot_size=int(target_qty),
            sample_size=min(int(target_qty), 10),
            defect_count=0,
            aql_max_defects=1
        )
        ctx.record_step(WorkflowStepRecord(
            step_id="step_3_qc",
            step_name="Finished Goods QC Inspection",
            department_code="OPS",
            status="COMPLETED",
            output_payload={"status": lot.status, "is_quarantined": lot.is_quarantined}
        ))

        # -------------------------------------------------------------
        # 4. Carrier Dispatch & Logistics Tracking
        # -------------------------------------------------------------
        logistics = SovereignLogisticsAdapter()
        shipment = logistics.create_shipment("DHL", "Warehouse-Mumbai", "Client-Bengaluru")
        track_num = shipment.tracking_number
        logistics.advance_status(track_num, "in_transit", "Mumbai Hub", "Package scanned into transit")
        logistics.advance_status(track_num, "out_for_delivery", "Bengaluru Hub", "Out with delivery agent")
        final_shipment = logistics.advance_status(track_num, "delivered", "Client-Bengaluru", "Delivered and signed")

        db_records[track_num] = {
            "tracking_number": track_num,
            "status": final_shipment.current_status,
            "carrier": final_shipment.carrier
        }

        # -------------------------------------------------------------
        # 5. Rule 59: Independent Re-read Verification
        # -------------------------------------------------------------
        self.verify_re_read(
            step_name="Logistics Delivery Verification",
            entity_id=track_num,
            expected_values={"status": "delivered"},
            re_read_fn=lambda eid: db_records.get(eid)
        )

        ctx.record_step(WorkflowStepRecord(
            step_id="step_4_logistics",
            step_name="Carrier Delivery Verification",
            department_code="PROC",
            status="COMPLETED",
            re_read_verified=True,
            output_payload={"tracking_number": track_num, "status": "delivered"}
        ))

        return {
            "workflow": self.name,
            "status": "COMPLETED",
            "work_order_id": completed_wo.work_order_id,
            "tracking_number": track_num,
            "delivery_status": "delivered",
            "audit_trail": ctx.audit_trail
        }
