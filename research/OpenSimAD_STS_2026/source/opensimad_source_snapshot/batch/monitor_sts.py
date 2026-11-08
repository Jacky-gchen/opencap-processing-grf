import csv
import json
import re
import subprocess
import argparse
from pathlib import Path
from collections import Counter

ROOT = Path.home() / "sts_sweep_v1"
REGISTRY = Path.home() / "sts_experiment_registry.csv"

parser = argparse.ArgumentParser()
parser.add_argument("--live", type=int, default=8)
args = parser.parse_args()

configs = {
    c["ID"]: c
    for c in json.loads(
        (ROOT / "sts_sweep_manifest.json").read_text()
    )
}

with REGISTRY.open(newline="") as f:
    registry = {
        r["ID"]: r
        for r in csv.DictReader(f)
        if r["ID"] in configs
    }

assert len(registry) == 72

def execute(command, timeout=30):
    try:
        p = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return p.stdout if p.returncode == 0 else ""
    except subprocess.TimeoutExpired:
        return ""

constraint = (
    "(ClusterId == 12111603 || "
    "ClusterId == 12111608)"
)

queue_output = execute([
    "condor_q",
    "-constraint", constraint,
    "-af", "ClusterId", "ProcId", "JobStatus"
])

history_output = execute([
    "condor_history",
    "-constraint", constraint,
    "-af", "ClusterId", "ProcId",
    "JobStatus", "ExitCode"
])

statuses = {}
exit_codes = {}

status_names = {
    "1": "IDLE",
    "2": "RUNNING",
    "3": "REMOVED",
    "4": "COMPLETED",
    "5": "HELD",
    "6": "TRANSFERRING",
    "7": "SUSPENDED",
}

for line in history_output.splitlines():
    p = line.split()
    if len(p) >= 3:
        jid = f"{p[0]}.{p[1]}"
        statuses[jid] = status_names.get(p[2], p[2])
        if len(p) >= 4:
            exit_codes[jid] = p[3]

for line in queue_output.splitlines():
    p = line.split()
    if len(p) >= 3:
        jid = f"{p[0]}.{p[1]}"
        statuses[jid] = status_names.get(p[2], p[2])

summary = Counter(
    statuses.get(r["Cluster"], "UNKNOWN")
    for r in registry.values()
)

print("\n========== STS SWEEP STATUS ==========")
print("Total experiments:", len(registry))

for status in [
    "IDLE", "RUNNING", "COMPLETED",
    "HELD", "TRANSFERRING",
    "REMOVED", "SUSPENDED", "UNKNOWN"
]:
    if summary[status]:
        print(f"{status:14s}: {summary[status]}")

print("\n========== IMPORTANT JOBS ==========")

priority = [
    "E015", "E018",
    "E039", "E063"
]

for eid in priority:
    r = registry[eid]
    jid = r["Cluster"]
    c = configs[eid]

    print(
        f"{eid} {jid:14s} "
        f"{statuses.get(jid, 'UNKNOWN'):12s} "
        f"profile={c['profile']:12s} "
        f"mesh={c['meshDensity']} "
        f"COP={c['COP_objective_enabled']} "
        f"window={c['window']}"
    )

problem_jobs = [
    (eid, r["Cluster"], statuses.get(r["Cluster"]))
    for eid, r in registry.items()
    if statuses.get(r["Cluster"]) in ["HELD", "REMOVED"]
    or (
        statuses.get(r["Cluster"]) == "COMPLETED"
        and exit_codes.get(r["Cluster"]) not in [None, "0"]
    )
]

if problem_jobs:
    print("\n========== JOBS NEEDING ATTENTION ==========")
    for item in problem_jobs[:20]:
        print(*item)

print("\n========== LIVE IPOPT SNAPSHOTS ==========")

# Prioritize pilots, then sample across the sweep.
ordered = priority + [
    eid for eid in sorted(configs)
    if eid not in priority
]

running = [
    eid for eid in ordered
    if statuses.get(registry[eid]["Cluster"]) == "RUNNING"
]

for eid in running[:args.live]:
    jid = registry[eid]["Cluster"]

    output = execute(
        ["condor_tail", "-maxbytes", "5000", jid],
        timeout=20
    )

    matches = []

    for line in output.splitlines():
        m = re.match(
            r"^\s*(\d+)\s+"
            r"([0-9.eE+-]+)\s+"
            r"([0-9.eE+-]+)\s+"
            r"([0-9.eE+-]+)\s+",
            line
        )
        if m:
            matches.append(m.groups())

    if matches:
        iteration, objective, primal, dual = matches[-1]

        print(
            f"{eid} {jid} "
            f"iter={iteration:>5s} "
            f"objective={float(objective):.4g} "
            f"inf_pr={float(primal):.3e} "
            f"inf_du={float(dual):.3e}"
        )
    else:
        print(f"{eid} {jid}: preparing / no IPOPT rows available")

print("\nReminder: IPOPT convergence requires final solver status.")
print("Low primal infeasibility alone is not sufficient.")
