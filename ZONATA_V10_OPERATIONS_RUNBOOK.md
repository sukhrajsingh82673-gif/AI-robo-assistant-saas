# ZONATA V10 OPERATIONS RUNBOOK
## Enterprise Production Operating Procedures & SRE Runbook

**Document Version**: 1.0.0  
**Target Audience**: Enterprise SREs, Platform Operators & Sovereign Infrastructure Leads  
**Classification**: OPERATIONAL PROCEDURES  

---

## 1. System Startup & Preflight Procedure

### SOP-01: Production Cold Boot
- **Trigger**: System initialization or server restart.
- **Preconditions**: `production.env.example` adapted to active `.env` or system environment.
- **Commands**:
  ```bash
  # 1. Execute startup preflight check
  python3 -c "from core.production_config import ProductionConfigValidator; \
  res = ProductionConfigValidator.run_startup_preflight(); \
  print('Preflight:', res['preflight_status']); \
  assert res['passed']"

  # 2. Launch API Daemon
  python3 api_server.py 8080
  ```
- **Expected Result**: API daemon binds to `0.0.0.0:8080`.
- **Verification**: `curl -s http://localhost:8080/metrics` returns HTTP 200.
- **Rollback**: Halt process, inspect logs in `storage/logs/`.
- **Escalation**: Notify SRE On-Call.

---

## 2. Emergency KillSwitch Activation Procedure

### SOP-02: Level-Specific KillSwitch Engagement
- **Trigger**: Adversarial attack, runaway mutations, or suspected data breach.
- **Preconditions**: Operator has authenticated shell or admin access.
- **Commands**:
  ```bash
  # Engage Global KillSwitch
  python3 -c "from core.killswitch_matrix import KillSwitchMatrix, KillSwitchLevel; \
  ks = KillSwitchMatrix('tnt_primary'); \
  ks.activate(KillSwitchLevel.GLOBAL, '*', 'Emergency Operator Blackout'); \
  print('Global KillSwitch Engaged.')"
  ```
- **Expected Result**: All autonomous mutations, worker jobs, and model calls halt immediately.
- **Verification**: Actions fail with `KillSwitchEngagedException`.

---

## 3. Secret Rotation Procedure

### SOP-03: Provider Secret Rotation
- **Trigger**: 90-day secret rotation policy or credential compromise.
- **Commands**:
  ```bash
  python3 -c "from core.secret_vault import SecretVault; \
  vault = SecretVault('tnt_primary'); \
  vault.rotate_secret('secret://tnt_primary/sec_pms_key', 'new_secure_secret_value'); \
  print('Secret Rotated.')"
  ```
- **Verification**: Inspect audit log in `enterprise_secret_access_audit`.
