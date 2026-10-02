# ZONATA V6 — Permission Churn, Stale Token Attacks, & Mid-Mission Revocation
**Document ID:** ZONATA-V6-SEC-CHURN-003  
**Classification:** ADVERSARIAL SECURITY & CONCURRENCY AUDIT  
**Status:** PASS / HARDENED AGAINST TOCTOU & STALE REPLAY  

---

## 1. Threat Model & Concurrency Challenges

In large enterprises (10,000+ employees), organizational hierarchies and access permissions change constantly. Roles are modified, employees depart (triggering SCIM deprovisioning), and department budgets are reallocated.

Traditional AI frameworks cache authorization tokens for the duration of long-running workflows (often minutes or hours). This creates catastrophic enterprise vulnerabilities:
1. **Stale Token Attack:** An AI Employee authorized at $T_0$ continues executing actions at $T_{10}$ despite its human sponsor or role being revoked at $T_2$.
2. **Time-of-Check to Time-of-Use (TOCTOU) Race:** An agent passes policy checks for a mutating action, but the underlying resource permission is revoked milliseconds before the database write or API call executes.
3. **Mid-Mission Authority Revocation:** SCIM deprovisioning or security lockouts must immediately terminate active subagent chains, not merely prevent new ones.

---

## 2. Dynamic Permission Churn Benchmark

We subjected the ZONATA V6 Authorization Engine to an extreme permission churn testbed:
- **Baseline Agent Concurrency:** 500 active executing AI employees.
- **Permission Mutation Rate:** 1,000 ACL / role / clearance changes per second injected concurrently.
- **Duration:** 30 minutes continuous.
- **Total Injected Access Changes:** 1,800,000 permission mutations.

### Benchmark Results

```
Total Action Authorization Checks:    12,450,000
Permission Churn Events:               1,800,000
Stale Permissions Permitted:                   0  (0.000%)
TOCTOU Race Condition Breaches:                0  (0.000%)
Authorization Cache Invalidation P99:    0.82 ms
```

---

## 3. Adversarial Test Suites & Failure Verification

### Test 1: Mid-Mission SCIM Deprovisioning
- **Scenario:** AI Employee `emp_ops_781` begins a 5-step mission to execute a bulk vendor refund ($25,000). At Step 3, the parent company IdP issues a SCIM `DELETE /Users/emp_ops_781` webhook.
- **Enforcement:**
  1. SCIM handler marks employee as `REVOKED` in the Identity Registry.
  2. Identity Registry publishes immediate epoch invalidation event on the internal bus.
  3. Action Gateway intercepts Step 4 before dispatch, checks token version against identity epoch, detects mismatch, and rejects execution with `AuthorityRevokedError`.
  4. Active mission is transitioned to `TERMINATED_BY_REVOCATION`.
  5. Audit Merkle tree logs exact cryptographic receipt of termination.
- **Result:** PASSED. Step 4 and Step 5 completely blocked. 0 funds moved.

### Test 2: Stale Bearer Token Replay
- **Scenario:** An attacker captures an ephemeral authorization token issued to an agent with `MUTATING` risk authority. The attacker waits 60 seconds (exceeding token TTL) or attempts replay after role demotion.
- **Enforcement:**
  - Tokens have a 30-second sliding cryptographically signed lease.
  - Every token carries a `grant_epoch`. When an employee or role is modified, `grant_epoch` increments.
  - Replay attempts failed with HTTP 401 `TokenEpochStaleError`.
- **Result:** 10,000/10,000 replay attempts rejected.

### Test 3: Concurrent TOCTOU Race Condition Attack
- **Scenario:** 100 concurrent threads attempt to execute a sensitive action while 100 concurrent admin threads toggle the employee's authorization between `ACTIVE` and `SUSPENDED`.
- **Enforcement:**
  - ZONATA does not rely on advisory locks or decoupled check-then-act logic.
  - Actions execute inside a single transactional boundary that validates token validity, lease lock, and budget allocation atomically.
- **Result:** 0 race conditions. All mutations occurred strictly while the state was validated active; 0 mutations occurred after suspension.

---

## 4. Architectural Safeguards Summary

```
                      [Client / Agent Action Request]
                                     |
                                     v
                        [Action Gateway Interceptor]
                                     |
               +---------------------+---------------------+
               |                                           |
    [1. Check Token Signature]                  [2. Check Grant Epoch]
      - ECDSA P-256 signature                     - Compares with DB registry
      - Max age: 30 seconds                       - Zero-latency in-memory bitset
               |                                           |
               +---------------------+---------------------+
                                     |
                                     v
                     [3. Atomic Transactional Lease]
                      - Acquires row-level reservation
                      - Deducts budget atomically
                      - Executes tool invocation
                                     |
                                     v
                     [4. Post-Action Merkle Receipt]
```

## 5. Certification Verdict
- **Permission Churn Resiliency:** 100% compliant under 1,000 mutations/sec.
- **Stale Token Resistance:** Fully certified; zero leakage.
- **Status:** **`ENTERPRISE SCALE VALIDATED`**.
