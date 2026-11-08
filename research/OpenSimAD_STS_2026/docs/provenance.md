# Provenance and audit trail

## Observed jobs and research environment

| Group | Cluster | Submitted | `condor_history` JobStatus=4 | Archives present |
|---|---|---:|---:|---:|
| STS pilots E015 and E018 | 12111603 | 2 | 2 | 2 |
| Other STS sweep jobs | 12111608 | 70 | 70 | 70 |
| Walking E111–E126 | 12111630 | 16 | 16 | 16 |

`JobStatus=4` means HTCondor finished the job; it does **not** mean IPOPT converged. All 88 were submitted before the audit. Job mappings for the 70-job cluster must be joined by the registry or `remaining_ids.txt`, not inferred from ID arithmetic.

**Known exact mapping:** `E015 → 12111603.0`, `E018 → 12111603.1`; remaining cases in cluster 12111608 follow `remaining_ids.txt`. E111–E126 belong to 12111630.

## Bundle hashes observed in October 12 output

- STS sweep bundle: `b66e6d93296dea4c352fab0cc0d3ebf3f842d8a3361287609d06982976399b88`
- Walking multi-subject bundle: `a3430ad9c2114d88091e95268e4072c77c37a6d9465de4b46dd3a72d18e81bb2`
- Locally downloaded CHTC review archive (not present in this closeout): `44835783387ca977ca6679475a1e7b43f217fa388855f878465db124c777a4ec`

Original registry: `~/sts_experiment_registry.csv` on `ap2001.chtc.wisc.edu`.

Original files: `~/sts_sweep_v1/sts_sweep_manifest.json`, `sts_sweep_outcomes.csv`, `remaining_ids.txt`, result archives; and `~/sts_walking_multi/walking_multi_manifest.json`, `walking_ids.txt`, result archives.

The October 12 terminal collector recorded **50 STS IPOPT optimal**, **15 iteration-limit**, **7 step-computation error**. For walking, the 16 `EXIT:` messages were recorded by ID. This closeout was created from the shared handoff and terminal output; it did **not** independently read every CHTC results archive.

## Fixed STS configuration

- Subject2 lab STS trial `STS1`, HRNet two-camera IK; measured laboratory external force inputs.
- Model family: `LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim`, adjusted for contact.
- `sts_grf`, torque-driven, pelvis residuals allowed, periodic constraints removed, heel vertical force minimum set to zero.
- Mesh densities: 25/50/100; IPOPT tolerance: 1e-2/1e-3; max 10,000 iterations.
- Profiles: Emily (1000/100/0.1), STS-inspired (50/10/50), intermediate (200/30/2) for position/velocity/acceleration weights.
- GRF tracking 0.001, pelvis residual weight 0.001, coordinate excitation weight 10. COP-ON tracking/monotonic weights 300/0.001; COP-OFF both zero.
- Original and buffered STS windows; buffered is 0.17–1.81 s. Original bounds are algorithmically segmented; do not treat nominal 0.47–1.51 s as verified for every archive.

## Why the manifest in this folder is marked reconstructed

The October 10 handoff supplied the full loop order and first eight IDs. We reconstructed ID→factor mapping to calculate descriptive rates. **For definitive provenance**, replace this file with the real CHTC JSON/CSV manifest and verify matching configurations. The per-ID IPOPT success list is an independent transcription from the October 12 collector output.

The handoff and original source code must remain the authority for implementation-specific behavior. Generated model variants, `.mot` and `.csv` simulation outputs and calibrated force axes cannot be inferred from the research summary alone.
