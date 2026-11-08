# Biomechanical validation protocol and unresolved questions

## Four categories must not be conflated

1. **Scheduler outcome:** HTCondor completed/transferred archive.
2. **Solver outcome:** IPOPT exact final `EXIT:` status, iterations, scaled and unscaled constraint/dual values.
3. **Mechanical consistency:** reasonable net force balance and pelvis residual magnitudes; no numerical dynamics violations in the accepted solution.
4. **Biomechanical plausibility:** realistic kinematics, floor contact, no foot sliding or teleportation, credible GRF/COP trajectories, and acceptable joint mechanics.

## Minimum plots and metrics for converged STS candidates

- Overlay IK vs simulated pelvis translation, pelvis tilt, trunk/hip/knee/ankle angles, with RMSE in a **shared verified time interval**.
- Compare laboratory vs optimized GRF for each foot and each component (especially vertical Y) after verifying coordinate conventions and timestamps. Report RMSE and/or MAE in N and normalized BW.
- Compare COP AP and ML only during loaded frames; guard against unphysical COP when vertical force tends to zero.
- Plot/resummarize pelvis residual force/moment RMS and peaks, normalized to body weight and bodyweight×height where appropriate.
- Visualize `kinematics_activations_STS1_E###_torqueDriven_STS.mot` using the corresponding `...adjusted_contacts.osim`; check seat-rise, foot placement, support transfer and foot drift.
- Compare one-factor contrasts: **E015 vs E017 (COP ON/OFF, original)**, **E017 vs E018 (window original/buffered, COP OFF)**. Do not attribute E015 vs E018 differences solely to COP because both COP setting and window differ.

Historical output layout differs: E015 used `OpenSimData/Dynamics/STS1_rep0/`; E018 used `OpenSimData/Dynamics/STS1/`.

## Walking mask investigation

Every force-derived case (E112, E114, E116, E118, E120, E122, E124, E126) converged. All paired marker-mask cases did not. Differences are in COP-validity masking, **not** fully force-derived gait-event detection.

For E111 vs E112, effective metadata showed right valid frames 97 vs 99 and left valid frames 89 vs 80; recorded marker/force disagreement counts were right 2, left 23. Extract exact frame indices and plot whether disagreements cluster near toe-off/heel-strike; verify `np.isfinite(stance)` semantics and mask alignment.

A converged walking case still requires visual gait inspection (E009 was a counterexample). Check whether force masks introduce knowledge of measured contact unavailable for video-only deployments.

## Decisions at research closeout

- **Completed:** submission audit (88/88 completed), solver-status classification (STS 50/72, walking 8/16), source archive SHA recording, preservation of experiment IDs.
- **Incomplete:** archive-by-archive biomechanical validation, robust ranking by GRF/COP errors and residuals, visual OpenSim animation review, subject-specific gait plausibility, exact failure type mapping for 22 STS jobs in this transcribed snapshot.
- **Deferred:** E010–E014 and E087–E110. They were not submitted; no reason to resubmit completed jobs or expand runs until the retained solutions are evaluated.

## Recommended next study, only if the project resumes

Investigate COP objective terms separately (tracking vs monotonic), residual weight sensitivity, force/COP interval masking and initialization. Base each case on a specifically documented mechanical or solver failure from the existing archive. Use new IDs, immutable input bundle hash, source revision, true per-job registry mapping, and measured biomechanics.
