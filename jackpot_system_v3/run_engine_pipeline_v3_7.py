#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import os

KITS_ROOT = "kits"

# ---------------------------------------------------------
# UTIL: Discover kit folders
# ---------------------------------------------------------
def discover_kits(root):
    if not os.path.isdir(root):
        return []

    return [
        os.path.join(root, p.name)
        for p in os.scandir(root)
        if p.is_dir() and not p.name.startswith("__")
    ]


# ---------------------------------------------------------
# PIPELINE STEP RUNNER
# ---------------------------------------------------------
def run_step(description, command, extra_args=None):
    print("\n====================================================")
    print(f" RUNNING: {description}")
    print("====================================================\n")

    cmd = [sys.executable, command]
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\n❌ {description} FAILED. Pipeline halted.\n")
        sys.exit(result.returncode)

    print(f"\n✅ {description} PASSED.\n")


# ---------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------
def main():

    # 1. Raw Data Sentinel
    run_step(
        "SENTINEL_ENGINE_v3_7 (Raw Data Integrity Check)",
        os.path.join("audit", "SENTINEL_ENGINE_v3_7.py"),
    )

    # 2. Discover kits
    kit_paths = discover_kits(KITS_ROOT)
    if not kit_paths:
        print("[PIPELINE] No kit folders found. Nothing to enrich.")
        sys.exit(0)

    print("[PIPELINE] Kits detected for enrichment:")
    for p in kit_paths:
        print(f"  - {p}")

    # 3. ENRICH
    run_step(
        "ENRICH_v3_7 (Engine Processing)",
        "ENRICH_v3_7.py",
        extra_args=kit_paths,
    )

    # 4. ✅ PRODUCTION SCRIBE (FINAL – SINGLE SOURCE OF TRUTH)
    run_step(
        "SCRIBE_PRODUCTION_v3_7 (Schema + Field Validation)",
        os.path.join("audit", "SCRIBE_PRODUCTION_v3_7.py"),
    )

    # 5. ORACLE
    run_step(
        "ORACLE_v3_7 (Overlay Validation)",
        "ORACLE_v3_7.py",
    )

    # 6. Hitlog Sentinel
    run_step(
        "SENTINEL_HITS_v3_7 (Forecast Hit Validation)",
        os.path.join("audit", "SENTINEL_HITS_v3_7.py"),
    )

    print("\n====================================================")
    print(" 🎉 PIPELINE COMPLETE — ALL CHECKS PASSED SUCCESSFULLY ")
    print("====================================================\n")


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
