# STS GRF OpenSimAD Validation Handoff

## Goal

Validate the new torque-driven `sts_grf` OpenSimAD formulation using laboratory-measured STS data before testing GaitDynamics-derived external loads.

Planned sequence:

1. Lab mocap IK + measured GRF/COP -> `sts_grf`
2. GaitDynamics GRF/COP -> `sts_grf`
3. Downstream Static Optimization later

---

## Repository

Repository:
`https://github.com/Jacky-gchen/opencap-processing-grf`

Branch:
`sts-grf-setup-review`

Important development commits:

- `d5501ad` - add `sts_grf` OpenSimAD setup
- `66d36c2` - add STS GRF tracking example
- `6b6e6ff` - fix COP mask parsing for variable MOT headers
- `c1f81d0` - add subject2 STS CHTC validation test

---

## CHTC Environment

Container:

`/staging/g/gchen293/opencap.sif`

Verified environment:

- Python 3.11.15
- NumPy 1.23.5
- CasADi 3.7.2
- OpenSim 4.5

OpenCap authentication is stored locally in `.env`.
`.env` is ignored by Git and must never be committed.

---

## Test Dataset

Uhlrich/OpenCap lab-validation subject2, trial `STS1`.

Subject:

- mass: 78.2 kg
- height: 1.96 m

Inputs:

- `STS1.mot` - mocap IK
- `STS1_forces.mot` - measured force plates
- `STS1.trc`
- `LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim`

Raw subject data are not committed to GitHub.

---

## STS Segmentation

Existing `segment_STS()` was used.

Detected periodic full STS windows:

- rep0: 0.47-1.51 s
- rep1: 2.13-3.16 s
- rep2: 3.79-4.73 s
- rep3: 5.31-6.28 s
- rep4: 6.93-7.99 s

Current validation run uses:

`repetition = 0`

so the simulated window is:

`0.47-1.51 s`

---

## COP Mask Fix

`getCOP_masks()` originally assumed:

`skiprows=11`

This was incompatible with `STS1_forces.mot` and produced:

- force samples: 17219
- COP mask samples: 17214

The function was changed to use the repository's general
`storage_to_dataframe()` / `storage_to_numpy()` parser.

After the fix:

- force samples: 17219
- right COP mask: 17219
- left COP mask: 17219

---

## Test 1: Measured Lab GRF/COP

Case:

`sts_grf_lab_measured_v1`

CHTC cluster:

`11948699`

Resources:

- CPU only
- 4 CPUs
- 16 GB RAM
- 12 GB disk

The complete CHTC job executed successfully, including:

- model adjustment
- contact model generation
- OpenSimAD external-function generation
- IPOPT optimization
- result export

However, the optimization did NOT reach a feasible solution.

IPOPT result:

`Infeasible_Problem_Detected`

Approximately:

- iterations: 60
- unscaled objective: 800.13
- unscaled constraint violation: 5.0

Objective contributions:

- GRF tracking: 55.61%
- position tracking: 26.59%
- pelvis residuals: 8.46%
- COP tracking: 6.36%
- velocity tracking: 2.97%

The non-convergent solution was successfully exported.

---

## Important Diagnostic

At the initial simulated frame, t = 0.47 s:

Measured force-plate vertical GRF:

- right Fy: ~585.8 N
- left Fy: ~635.9 N
- total: ~1221.6 N

OpenSimAD contact GRF:

- right: approximately 0 N
- left: approximately 0 N

This is the major current red flag.

At the final frame, t = 1.51 s, OpenSimAD was generating substantial
foot-ground forces, so the contact model is capable of producing GRFs but
appears inconsistent with the measured motion/ground relationship over at
least part of the trajectory.

GRF RMSE over the non-convergent window:

- right Fx: ~49.3 N
- right Fy: ~232.6 N
- right Fz: ~53.6 N
- left Fx: ~52.8 N
- left Fy: ~253.5 N
- left Fz: ~52.4 N

Pelvis residual ranges:

Forces:

- tx: -82.1 to +389.6 N
- ty: -383.9 to +702.8 N
- tz: -32.1 to +61.5 N

Moments:

- pelvis tilt: -154.3 to +45.4 Nm
- pelvis list: -42.9 to +66.9 Nm
- pelvis rotation: -13.8 to +20.3 Nm

The large residuals appear to compensate for the mismatch between the
measured external loads and the OpenSimAD foot-ground contact solution.

---

## Generated Model

OpenSimAD successfully generated:

- `LaiArnoldModified2017_poly_withArms_weldHand_scaled_adjusted.osim`
- `LaiArnoldModified2017_poly_withArms_weldHand_scaled_adjusted_contacts.osim`
- `ExternalFunction/F.cpp`
- `ExternalFunction/F.py`
- `ExternalFunction/F_map.npy`

The model-adjustment log did not show an obvious failure.

---

## Next Step

Do NOT tune tracking weights or loosen IPOPT yet.

First investigate the OpenSimAD foot-ground contact geometry and ground
alignment for this subject/model.

Primary question:

Why does the generated contact model produce approximately zero foot GRF at
t = 0.47 s when the laboratory force plates measure approximately 1222 N?

Inspect:

1. foot contact sphere definitions and locations
2. sphere radii
3. ground half-space definition
4. global foot/contact-sphere height at t = 0.47 s
5. consistency between mocap IK vertical position and OpenSimAD ground plane

Only after resolving this should Test 1 be rerun.

Test 2 with GaitDynamics loads should remain paused until the measured-lab
baseline behaves correctly.
