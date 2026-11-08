from pathlib import Path
from collections import Counter
import csv
import re
import shutil
import tempfile
import os

home = Path.home()
root = home / "sts_sweep_v1"
registry = home / "sts_experiment_registry.csv"

with registry.open(newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)

def extract(pattern, text):
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches[-1] if matches else ""

outcomes = []

for row in rows:
    eid = row["ID"]

    if not (15 <= int(eid[1:]) <= 86):
        continue

    cluster = row["Cluster"].split(".")[0]

    logfile = root / "logs" / f"{eid}_{cluster}.out"

    if not logfile.exists():
        continue

    text = logfile.read_text(errors="replace")

    exit_status = extract(r"EXIT:\s*(.+)", text)
    iterations = extract(
        r"Number of Iterations\.*:\s*(\d+)", text
    )

    constraint = extract(
        r"Constraint violation\.*:\s*"
        r"([0-9.eE+-]+)\s+([0-9.eE+-]+)",
        text
    )

    nlp_error = extract(
        r"Overall NLP error\.*:\s*"
        r"([0-9.eE+-]+)\s+([0-9.eE+-]+)",
        text
    )

    if exit_status:
        if "Optimal Solution Found" in exit_status:
            status = "Converged - Optimal Solution Found"
        else:
            status = "IPOPT - " + exit_status.strip()
    else:
        status = "No final IPOPT status yet"

    if exit_status:
        row["Status"] = status

        if iterations:
            row["Iterations"] = iterations

        if constraint:
            row["UnscaledConstraintViolation"] = constraint[1]

    outcomes.append({
        "ID": eid,
        "Cluster": row["Cluster"],
        "Status": status,
        "Iterations": iterations,
        "ScaledConstraintViolation":
            constraint[0] if constraint else "",
        "UnscaledConstraintViolation":
            constraint[1] if constraint else "",
        "ScaledNLPError":
            nlp_error[0] if nlp_error else "",
        "UnscaledNLPError":
            nlp_error[1] if nlp_error else "",
        "ArchivePresent": (
            root / "results" / f"{eid}_results.tar.gz"
        ).exists()
    })

shutil.copy2(
    registry,
    str(registry) + ".bak_before_STS_collection"
)

with tempfile.NamedTemporaryFile(
    mode="w", newline="",
    dir=registry.parent, delete=False
) as f:
    temporary = f.name
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

os.replace(temporary, registry)

output = root / "sts_sweep_outcomes.csv"

with output.open("w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=list(outcomes[0])
    )
    writer.writeheader()
    writer.writerows(outcomes)

summary = Counter(r["Status"] for r in outcomes)

print("=== COLLECTED STS RESULTS ===")
for status, count in summary.items():
    print(f"{status}: {count}")

print("\n=== CONVERGED EXPERIMENTS ===")
for r in outcomes:
    if r["Status"].startswith("Converged"):
        print(
            r["ID"],
            "iterations =", r["Iterations"],
            "scaled NLP error =", r["ScaledNLPError"],
            "archive =", r["ArchivePresent"]
        )

print("\nSaved:", output)
print("Registry updated:", registry)
