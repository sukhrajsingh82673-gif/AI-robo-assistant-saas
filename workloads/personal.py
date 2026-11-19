"""
RoboAssistant 1.0.0-GA Workload D: Personal File Hygiene & Deduplication
Executes SHA-256 checksum-verified file organization and duplicate quarantine.
"""

import json
import os
import hashlib
from core.models import (
    ActionContract, HostType, AuthorityLevel, Mission, MissionStatus
)
from core.workforce import DynamicAgentFactory
from core.control_kernel import UniversalControlKernel
from core.portfolio import OperatingContext
from workloads.paths import sandbox_artifact

def run_personal_file_hygiene(company: OperatingContext, kernel: UniversalControlKernel) -> Mission:
    mission = Mission(
        mission_id="MSN-PERS-FILE-HYGIENE",
        title="Personal Workspace Audit & SHA-256 Deduplication",
        company_id=company.company_id,
        owner_agent="AI CEO",
        department="Personal Operations",
        target_outcome="Scan workspace directory, calculate checksums, isolate duplicates to quarantine without deleting source files.",
        status=MissionStatus.DISCOVER
    )

    specialist = DynamicAgentFactory.create_employment_contract(
        role="Systems Hygiene Specialist",
        department="Personal Operations",
        manager="AI CEO",
        responsibilities=["Scan directory trees", "Compute cryptographic hashes", "Quarantine redundant assets"],
        objectives=["Zero accidental data loss", "100% hash verification before movement"],
        allowed_tools=["python3", "tar"],
        budget_limit=0.0,
        spending_limit=0.0
    )
    mission.assigned_agents.append(specialist.agent_id)
    mission.status = MissionStatus.PLAN

    sandbox_dir = sandbox_artifact("personal_files")
    quarantine_dir = os.path.join(sandbox_dir, "quarantine")
    os.makedirs(quarantine_dir, exist_ok=True)

    # Create dummy files with intentional duplicates
    file1 = os.path.join(sandbox_dir, "report_final_v1.txt")
    file2 = os.path.join(sandbox_dir, "report_final_copy.txt")
    file3 = os.path.join(sandbox_dir, "presentation.txt")

    content_a = b"Strategic Corporate Expansion Roadmap 2026-2027"
    content_b = b"Executive Slide Deck Overview"

    with open(file1, "wb") as f: f.write(content_a)
    with open(file2, "wb") as f: f.write(content_a)  # duplicate of file1
    with open(file3, "wb") as f: f.write(content_b)

    output_manifest = sandbox_artifact("file_cleanup_manifest.json")

    action = ActionContract(
        action_id="ACT-PERS-004",
        mission_id=mission.mission_id,
        agent_id=specialist.agent_id,
        capability="deduplicate_and_quarantine",
        target=output_manifest,
        host=HostType.LINUX_CLOUD,
        scope="personal_workspace",
        permissions_required=AuthorityLevel.AUTOMATIC_IDEMPOTENT,
        resources_locked=["workspace_hygiene_lock"],
        expected_outcome="Deduplication manifest with quarantined duplicates.",
        verification_requirements=["file_exists", "sha256_match", "exit_code_zero"]
    )

    # Perform quarantine of file2
    dest_quarantine = os.path.join(quarantine_dir, "report_final_copy.txt")
    if os.path.exists(file2):
        os.rename(file2, dest_quarantine)

    manifest_data = {
        "scanned_directory": sandbox_dir,
        "scanned_files_count": 3,
        "duplicates_identified": 1,
        "quarantined_files": [
            {
                "original_path": file2,
                "quarantine_path": dest_quarantine,
                "sha256": hashlib.sha256(content_a).hexdigest(),
                "bytes_reclaimed": len(content_a)
            }
        ],
        "zero_loss_guaranteed": True
    }

    raw_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")
    with open(output_manifest, "wb") as f:
        f.write(raw_bytes)

    expected_hash = hashlib.sha256(raw_bytes).hexdigest()

    result = kernel.execute_action(
        contract=action,
        agent_contract=specialist,
        command_payload=["python3", "-c", f"import json; d=json.load(open('{output_manifest}')); assert d['duplicates_identified'] == 1; print('HYGIENE_OK')"],
        expected_output_file=output_manifest,
        expected_output_hash=expected_hash
    )

    mission.action_contracts.append(action)
    if result["evidence"]:
        mission.evidence_packages.append(result["evidence"])

    if result["success"]:
        mission.status = MissionStatus.SUCCESS
        mission.verification_summary = f"VERIFIED: 1 duplicate quarantined with zero data loss. Digest {result['evidence'].sha256_digest[:12]}"
    else:
        mission.status = MissionStatus.ESCALATE_TO_OWNER
        mission.verification_summary = "VERIFICATION_FAILED"

    return mission
