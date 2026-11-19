"""
RoboAssistant 1.0.0-GA Universal Control Kernel (AN - The Body)
ExecutionSupervisor, Typed ActionContracts, Resource Locks, and Host Mediation.
"""

import os
import signal
import subprocess
import time
import uuid
from typing import Dict, List, Optional, Set, Any
from .models import (
    ActionContract, HostType, AuthorityLevel,
    EvidencePackage, PhysicalVerification, MissionStatus
)
from .physical_truth import PhysicalTruthEngine
from .evidence_ledger import EvidenceLedger
from .workforce import AgentEmploymentContract

class ResourceLockManager:
    def __init__(self):
        self._locks: Set[str] = set()

    def acquire(self, resources: List[str]) -> bool:
        for res in resources:
            if res in self._locks:
                return False
        for res in resources:
            self._locks.add(res)
        return True

    def release(self, resources: List[str]):
        for res in resources:
            self._locks.discard(res)

class UniversalControlKernel:
    """
    Bridge between AI Strategic Decisions and Physical Host Execution.
    No unmediated execution.
    """

    def __init__(self, evidence_ledger: EvidenceLedger):
        self.evidence_ledger = evidence_ledger
        self.lock_mgr = ResourceLockManager()

    def execute_action(
        self,
        contract: ActionContract,
        agent_contract: AgentEmploymentContract,
        command_payload: Optional[List[str]] = None,
        expected_output_file: Optional[str] = None,
        expected_output_hash: Optional[str] = None,
        killswitch_check: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Executes a typed ActionContract under strict supervision.
        Supports active cancellation propagation via killswitch_check.
        """
        # 1. Authority & Policy Validation
        if contract.capability in agent_contract.forbidden_actions:
            return {
                "success": False,
                "error": f"SECURITY_POLICY_VIOLATION: Action '{contract.capability}' is forbidden for agent {agent_contract.agent_id}",
                "status": "DENIED"
            }

        if contract.permissions_required == AuthorityLevel.NEVER_ALLOWED:
            return {
                "success": False,
                "error": "SECURITY_POLICY_VIOLATION: Operation classified as NEVER_ALLOWED.",
                "status": "BLOCKED"
            }

        # 2. Acquire Resource Locks
        if not self.lock_mgr.acquire(contract.resources_locked):
            return {
                "success": False,
                "error": f"RESOURCE_CONTENTION: Resources {contract.resources_locked} are currently locked by another process.",
                "status": "BLOCKED"
            }

        verifications: List[PhysicalVerification] = []
        exec_output = ""
        success = False

        try:
            # 3. Execution on target host
            if contract.host == HostType.LINUX_CLOUD:
                if command_payload:
                    proc = subprocess.Popen(
                        command_payload,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        start_new_session=True
                    )
                    timeout = 60.0
                    start_t = time.time()
                    aborted_by_ks = False

                    while proc.poll() is None:
                        if killswitch_check and killswitch_check():
                            aborted_by_ks = True
                            try:
                                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                            except Exception:
                                proc.kill()
                            try:
                                proc.wait(timeout=2.0)
                            except Exception:
                                pass
                            break
                        if time.time() - start_t > timeout:
                            try:
                                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                            except Exception:
                                proc.kill()
                            break
                        time.sleep(0.005)  # 5ms slice for responsive interruption

                    if aborted_by_ks:
                        try:
                            if proc.stdout:
                                proc.stdout.close()
                            if proc.stderr:
                                proc.stderr.close()
                        except Exception:
                            pass
                        exec_output = "PROCESS_ABORTED_BY_KILLSWITCH: Subprocess process tree terminated via SIGKILL upon KillSwitch engagement."
                        success = False
                        verifications.append(PhysicalVerification(
                            check_type="killswitch_abort",
                            target_path=" ".join(command_payload),
                            expected_val="ACTIVE",
                            actual_val="ABORTED",
                            verified=True,
                            details="Subprocess process tree killed immediately upon KillSwitch engagement"
                        ))
                    else:
                        stdout_str, stderr_str = proc.communicate()
                        exec_output = (stdout_str or "") + (stderr_str or "")
                        retcode = proc.returncode
                        proc_check = PhysicalVerification(
                            check_type="exit_code_zero",
                            target_path=" ".join(command_payload),
                            expected_val="0",
                            actual_val=str(retcode),
                            verified=(retcode == 0),
                            details=f"Exit code: {retcode}"
                        )
                        verifications.append(proc_check)
                        success = (retcode == 0)
                else:
                    success = True
            else:
                # Remote hosts (Windows, macOS Studio, Android, iOS Remote) are not
                # connected through this kernel. Reporting success here would be
                # fabricated physical evidence, so the contract fails closed.
                success = False
                exec_output = (
                    f"Remote host {contract.host.value} is not connected; "
                    "no remote execution channel is available."
                )
                verifications.append(PhysicalVerification(
                    check_type="remote_host_reachable",
                    target_path=contract.target,
                    expected_val="ACK",
                    actual_val="NOT_CONNECTED",
                    verified=False,
                    details=(
                        f"No execution channel is registered for host {contract.host.value}; "
                        f"contract {contract.action_id} was not dispatched."
                    )
                ))

            # 4. Physical Truth Engine checks if expected output file is declared
            if expected_output_file:
                file_check = PhysicalTruthEngine.verify_file_exists(expected_output_file)
                verifications.append(file_check)
                if file_check.verified and expected_output_hash:
                    hash_check = PhysicalTruthEngine.verify_sha256_match(expected_output_file, expected_output_hash)
                    verifications.append(hash_check)

        except Exception as e:
            success = False
            exec_output = f"EXECUTION_CRASH: {str(e)}"
        finally:
            self.lock_mgr.release(contract.resources_locked)

        # 5. Seal in Merkle Audit Ledger
        agent_id_val = agent_contract.agent_id
        evidence = self.evidence_ledger.seal_evidence(
            action_id=contract.action_id,
            mission_id=contract.mission_id,
            agent_id=agent_id_val,
            verifications=verifications,
            metadata={
                "target": contract.target,
                "host": contract.host.value,
                "expected_outcome": contract.expected_outcome,
                "execution_output": exec_output[:200]
            }
        )

        return {
            "success": success and (evidence.status != "PENDING_EVIDENCE"),
            "action_id": contract.action_id,
            "status": evidence.status.value,
            "evidence": evidence,
            "output": exec_output
        }
