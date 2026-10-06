"""
ZONATA Enterprise Database Deduplication & Integrity Script
Cleans up duplicate background missions, duplicate Nango connections,
duplicate external system connections, and applies canonical uniqueness indexes.
"""

import sqlite3
import os
import sys

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "roboassistant.db"))

def deduplicate():
    print(f"[*] Opening database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Deduplicate coworker_background_missions
    print("[*] Deduplicating coworker_background_missions...")
    rows = cursor.execute("""
        SELECT mission_id, tenant_id, company_id, prompt, status, created_at
        FROM coworker_background_missions
        ORDER BY created_at DESC
    """).fetchall()

    seen_missions = set()
    to_delete_missions = []
    for r in rows:
        norm_prompt = r["prompt"].strip().lower()
        key = (r["tenant_id"], r["company_id"], norm_prompt)
        if key in seen_missions:
            to_delete_missions.append(r["mission_id"])
        else:
            seen_missions.add(key)

    if to_delete_missions:
        cursor.executemany("DELETE FROM coworker_background_missions WHERE mission_id = ?", [(m,) for m in to_delete_missions])
        print(f"[-] Deleted {len(to_delete_missions)} duplicate missions.")
    else:
        print("[+] No duplicate missions found.")

    # 2. Deduplicate nango_connections
    print("[*] Deduplicating nango_connections...")
    conn_rows = cursor.execute("""
        SELECT connection_id, tenant_id, company_id, provider_id, status, created_at
        FROM nango_connections
        ORDER BY created_at DESC
    """).fetchall()

    seen_nango = set()
    to_delete_nango = []
    for r in conn_rows:
        key = (r["tenant_id"], r["company_id"], r["provider_id"].strip().lower())
        if key in seen_nango:
            to_delete_nango.append(r["connection_id"])
        else:
            seen_nango.add(key)

    if to_delete_nango:
        cursor.executemany("DELETE FROM nango_connections WHERE connection_id = ?", [(c,) for c in to_delete_nango])
        print(f"[-] Deleted {len(to_delete_nango)} duplicate nango connections.")
    else:
        print("[+] No duplicate nango connections found.")

    # 3. Deduplicate external_connections
    print("[*] Deduplicating external_connections...")
    ext_rows = cursor.execute("""
        SELECT connection_id, tenant_id, company_id, name, service_type, created_at
        FROM external_connections
        ORDER BY created_at DESC
    """).fetchall()

    seen_ext = set()
    to_delete_ext = []
    for r in ext_rows:
        key = (r["tenant_id"], r["company_id"], r["name"].strip().lower())
        if key in seen_ext:
            to_delete_ext.append(r["connection_id"])
        else:
            seen_ext.add(key)

    if to_delete_ext:
        cursor.executemany("DELETE FROM external_connections WHERE connection_id = ?", [(c,) for c in to_delete_ext])
        print(f"[-] Deleted {len(to_delete_ext)} duplicate external connections.")
    else:
        print("[+] No duplicate external connections found.")

    # 4. Add unique index or idempotency index if not exists
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_nango_tenant_comp_prov ON nango_connections(tenant_id, company_id, provider_id);")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_ext_conn_tenant_comp_name ON external_connections(tenant_id, company_id, name);")

    conn.commit()
    conn.close()
    print("[✓] Deduplication & database integrity complete.")

if __name__ == "__main__":
    deduplicate()
