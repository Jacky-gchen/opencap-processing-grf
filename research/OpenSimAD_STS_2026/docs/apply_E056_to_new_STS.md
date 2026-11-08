# Apply selected E056 settings to a NEW STS trial

**Selected settings:** [E056 configuration snapshot](../configs/E056_selected_config.json). **Supporting evidence:** [E056 selection and caveats](E056_selection_2026-11-08.md).

## Transferable settings (start with these, then validate)

- `motion_type=sts_grf`, torque-driven model; STS-inspired kinematic weights position=50, velocity=10, acceleration=50.
- Mesh density=100, IPOPT tolerance **0.01** (runner-specific `ipopt_tolerance=2`), max iterations=10000.
- GRF tracking weight=0.001, COP tracking weight=300, COP monotonic weight=0.001, pelvis residual weight=0.001.
- Coordinate excitation weight=10; other effective weights and bound values in the JSON snapshot.
- Allow pelvis residuals; disable periodic constraints; minimum heel vertical GRF 0.
- Source code should be pinned to the archived E056 runner checksum and compared with the branch's source snapshot. No claim that passing JSON directly to the runtime will configure these settings: the runner's wiring must be verified.

## Do NOT copy from subject 2

1. **Participant-specific model:** generate and verify scaling, contact sphere positions, masses/inertias, geometry and coordinate definitions for the new participant.
2. **Input motion:** acquire and process new STS marker/video/IK trajectories, using a documented time reference. Do not use old `STS1.mot`.
3. **External loads:** obtain new force plate records; verify right/left assignment, units, orientation, signs, COP, free moment and synchronization. Do not use old `STS1_forces.mot`.
4. **COP validity mask:** regenerate for the new force dataset and inspect near contact transitions. The original uses a force-derived mask; this depends on measured force plates, not video-only data.
5. **Time window:** re-identify the new trial's rising phase and buffer start/end. **0.17–1.81 s was E056-specific**, not a default for all STS recordings.
6. **Bounds and initial guess:** review `pelvis_ty` and `pelvis_tx` `env_bound=0.1`, contact assumptions and initialization for the new trial, rather than assuming feasibility.
7. **Reproducibility:** record the new experiment ID, input filenames/hashes, runner commit and SHA, requested/effective settings, model hash, solver exit, and full IPOPT log.

## Post-run quality gates

- Solver: IPOPT exit category; scaled NLP error versus tol, iteration count, primal/dual infeasibility history where available.
- Force/COP: resample reference and predictions onto a *shared, justified* interval with valid foot-contact masks; report per-foot GRF X/Y/Z RMSE, COP X/Z RMSE/bias, free moments and net force error. Do not infer full-trial accuracy from a short rise-phase slice.
- Kinematics: compare angles and pelvis translations against that trial's *own* IK and inspect animation for drift, penetration, end-frame artifacts and discontinuities.
- Mechanics: examine residual pelvis forces/moments and resulting inverse-dynamics moments before advancing to muscle static optimization.
- Compare a tolerance and/or COP-switch control case if results are unstable; one trial's ranking does not prove parameter optimality on other participants.

## Data retention and GitHub safety

The project repository is **public**. Keep raw participant markers, videos, force plates, identifiable model/motion files and bulk archives within approved institutional storage. GitHub should contain reusable source/configuration, sanitized metrics and methodology only. Back up the complete E056 output and your future trial archives separately because CHTC does not back them up.

## Final handoff status

E056 is the **selected baseline** for next-stage STS experimentation, not an independently validated biomechanical model and not yet a completed reusable new-subject pipeline. The settings snapshot is for controlled adaptation: it is not an executable configuration loader unless the OpenSimAD runner explicitly implements that interface.
