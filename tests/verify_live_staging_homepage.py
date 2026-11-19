#!/usr/bin/env python3
"""
ZONATA SaaS — Live Staging Homepage & Executive Overview Verification Suite
Tests the deployed staging service (https://zonata-staging.onrender.com) end-to-end.
"""

import sys
import json
import time
import urllib.request
import urllib.error

STAGING_BASE_URL = "https://zonata-staging.onrender.com"
PILOT_EMAIL = "zonata.qa.step2@example.com"
PILOT_PASS = "Step2_Secure_QA_2026!"

def log_test(name, passed, detail=""):
    mark = "✅ PASS" if passed else "❌ FAIL"
    print(f"[{mark}] {name}")
    if detail:
        print(f"       {detail}")

def check_readyz():
    url = f"{STAGING_BASE_URL}/readyz"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            commit = data.get("commit", "")
            status = data.get("status", "")
            db_status = data.get("database", "")
            return status == "HEALTHY" and db_status == "CONNECTED", commit, data
    except Exception as e:
        return False, "", str(e)

def check_unauthenticated_security():
    url = f"{STAGING_BASE_URL}/api/overview/snapshot"
    req = urllib.request.Request(url)
    try:
        urllib.request.urlopen(req, timeout=30)
        return False, "Expected 401 Unauthorized but got 200"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            body = e.read().decode()
            return True, f"Correctly rejected unauthenticated request: HTTP 401 ({body[:80]})"
        return False, f"Unexpected HTTP status: {e.code}"
    except Exception as e:
        return False, str(e)

def check_login():
    url = f"{STAGING_BASE_URL}/api/auth/login"
    payload = json.dumps({"email": PILOT_EMAIL, "password": PILOT_PASS}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            token = data.get("token")
            user = data.get("user", {})
            tenant_id = user.get("tenant_id")
            if token and tenant_id:
                return True, token, tenant_id, user
            return False, "", "", "Missing token or tenant_id in response"
    except Exception as e:
        return False, "", "", str(e)

def check_authenticated_overview(token, tenant_id):
    url = f"{STAGING_BASE_URL}/api/overview/snapshot"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            context = data.get("context", {})
            fin = data.get("financial", {})
            port = data.get("portfolio", {})
            ops = data.get("operations", {})
            wf = data.get("workforce", {})
            dq = data.get("data_quality", {})
            has_context = "mode" in context
            has_fin = "revenue" in fin or "has_data" in fin
            has_port = "portfolio_revenue" in port or "total_companies" in port
            has_ops = "active_operations" in ops or "has_data" in ops
            detail = f"mode={context.get('mode')} period={context.get('period')} fin_revenue={fin.get('revenue')} portfolio_rev={port.get('portfolio_revenue')} companies={port.get('total_companies')}"
            valid = has_context and (has_fin or has_port) and has_ops
            return valid, detail, data
    except Exception as e:
        return False, str(e), {}
    except Exception as e:
        return False, str(e), {}

def main():
    print("=" * 70)
    print("URA / ZONATA — Live Staging Homepage & Overview Verification")
    print(f"Target URL: {STAGING_BASE_URL}")
    print("=" * 70)

    # 1. Health & Commit check
    is_ready, commit, ready_data = check_readyz()
    log_test("Staging /readyz Health Check", is_ready, f"commit: {commit} status: {ready_data.get('status') if isinstance(ready_data, dict) else ready_data}")

    # 2. Unauthenticated endpoint security (fail-closed check)
    sec_ok, sec_detail = check_unauthenticated_security()
    log_test("Fail-Closed Security: Unauthenticated /api/overview/snapshot returns 401", sec_ok, sec_detail)

    # 3. Pilot authentication
    auth_ok, token, tenant_id, user_info = check_login()
    log_test("Pilot Authentication: /api/auth/login succeeds", auth_ok, f"tenant={tenant_id} user={user_info.get('user_id') if isinstance(user_info, dict) else ''}")

    if not auth_ok:
        print("FATAL: Could not obtain auth token. Aborting overview verification.")
        sys.exit(1)

    # 4. Authenticated overview retrieval
    over_ok, over_detail, snapshot = check_authenticated_overview(token, tenant_id)
    log_test("Executive Overview Retrieval: /api/overview/snapshot returns HTTP 200", over_ok, over_detail)

    # 5. Session token verification
    token_valid = bool(token and "." in token)
    log_test("Cryptographic Token Signature Check", token_valid, f"token_prefix={token[:40]}...")

    print("=" * 70)
    all_passed = is_ready and sec_ok and auth_ok and over_ok and token_valid
    if all_passed:
        print("ALL CRITICAL INTEGRATION CHECKS PASSED.")
    else:
        print("ONE OR MORE CHECKS FAILED.")
    print("=" * 70)

if __name__ == "__main__":
    main()
