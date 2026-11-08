#!/usr/bin/env python3
"""Verify transcription and print descriptive IPOPT outcome summaries.
Does not use CHTC, submit jobs, or modify inputs.
"""
import csv
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]

def read(name):
    with (ROOT / 'data' / name).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

sts = read('sts_outcomes_transcribed_2026-10-12.csv')
factors = read('sts_factorial_reconstructed_from_handoff.csv')
walk = read('walking_outcomes_transcribed_2026-10-12.csv')
assert len(sts) == len(factors) == 72
assert len(walk) == 16
assert {r['ID'] for r in sts} == {r['ID'] for r in factors}
assert len({r['ID'] for r in sts}) == 72
assert len({r['ID'] for r in walk}) == 16
lookup = {r['ID']: r for r in factors}

def isopt(r): return r['IPOPT_Optimal'].lower() == 'true'
print('STS:', sum(isopt(r) for r in sts), '/', len(sts))
for field in ['profile','meshDensity','ipopt_tolerance_exponent','COP_objective_enabled','window']:
    values = sorted({lookup[r['ID']][field] for r in sts})
    for value in values:
        group = [r for r in sts if lookup[r['ID']][field] == value]
        print(f'  {field}={value}: {sum(isopt(r) for r in group)}/{len(group)}')
for tol in ['2','3']:
    for enabled in ['True','False']:
        group = [r for r in sts if lookup[r['ID']]['ipopt_tolerance_exponent']==tol and lookup[r['ID']]['COP_objective_enabled']==enabled]
        print(f'  COP={enabled} tol=1e-{tol}: {sum(isopt(r) for r in group)}/{len(group)}')
print('Walking:', sum(isopt(r) for r in walk), '/', len(walk))
for mask in ['marker-derived','force-derived']:
    group = [r for r in walk if r['COP_mask_method']==mask]
    print(f'  {mask}: {sum(isopt(r) for r in group)}/{len(group)}')
