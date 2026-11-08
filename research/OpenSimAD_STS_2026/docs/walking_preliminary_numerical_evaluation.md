# Preliminary walking evaluation of Emily-style OpenSimAD GRF/COP tracking

**Status:** numerical reproduction and COP-mask sensitivity evaluation. **Not** a complete replication of Emily Miller's published results, nor a comprehensive biomechanical validation of gait.

This document separates the preliminary walking investigation (E009 and E111–E126) from the 72-case sit-to-stand (STS) investigation (E015–E086). Attribution to Emily's original upstream work is based on the preserved adapted runner; an exact original-source revision comparison is still needed before claiming a faithful reproduction of published results.

## Motivation

Emily Miller's updated GRF/COP-tracking approach was developed for walking. We used walking gait data as a baseline for testing whether this formulation would run with experimentally measured GRF/COP, and then investigated whether COP-validity masking affected IPOPT convergence. This work informed questions about force/COP tracking in our subsequent STS research, but did not by itself validate the STS formulation.

## Stage A: E009 walking positive control

The [E009 runner](../source/opensimad_source_snapshot/runners/run_E009.py) preserves a walking configuration based on Emily's GRF/COP tracking approach, with:

- `motion_type = 'walking_grf'`, torque-driven actuation.
- Subject 2 `walking1`, HRNet two-camera IK, a scaled LaiArnoldModified2017 model, and laboratory-measured GRF/COP.
- Gait events from `process_gait_data` and stance variables from `map_stance_phase`.
- Marker-derived COP validity masks:

```python
settings['CoP_mask']['right'] = np.isfinite(right_stance).astype(int)
settings['CoP_mask']['left']  = np.isfinite(left_stance).astype(int)
```

- Gait-event time boundaries, 6 Hz kinematic filtering, mesh density 50, position tracking weight 1000, and GRF tracking weight 0.001; other settings were inherited from the walking configuration.

**Observed result:** E009 reached IPOPT optimal termination. Qualitative visualization nevertheless showed an unrealistic right-foot movement near the start. Thus solver convergence alone did not establish biomechanical plausibility. No quantitative kinematic validation metric is available from this observation.

## Stage B: E111–E126 paired COP-mask test

The [walking experiment manifest](../source/opensimad_source_snapshot/metadata/walking_multi_manifest.json) defines **16 experiments**: eight subjects (3–10), each tested with two COP-mask methods. Both used `walking1`, `walking_grf`, torque-driven actuation, mesh density 50, encoded `ipopt_tolerance=3` (1e-3), and a 10,000-iteration cap.

The [runner](../source/opensimad_source_snapshot/runners/run_walking_multi.py) retained **marker-derived gait-event timing and stance percentages in both conditions**. It changed the *COP validity mask*, not the full gait-event detection process.

### Mask definitions

**Marker-derived:** a mask based on whether the computed stance entry is finite:

```python
marker_right = np.isfinite(right_stance).astype(int)
marker_left  = np.isfinite(left_stance).astype(int)
```

**Force-derived:** interpolate measured vertical GRF for each foot onto the gait-event timestamps and include COP tracking only above **20 N**:

```python
force_right = (np.interp(event_time, force_time, right_vertical,
                         left=0, right=0) > 20).astype(int)
force_left  = (np.interp(event_time, force_time, left_vertical,
                         left=0, right=0) > 20).astype(int)
```

### Observed IPOPT termination (October 12, 2026)

| COP mask method | IDs | IPOPT optimal | Nonoptimal failures |
|---|---|---:|---|
| Marker-derived | E111, E113, E115, E117, E119, E121, E123, E125 | **0/8** | 4 restoration failures; 3 step-computation errors; 1 iteration limit |
| Force-derived | E112, E114, E116, E118, E120, E122, E124, E126 | **8/8** | None recorded |

Source: [per-experiment walking solver outcomes](../data/walking_outcomes_transcribed_2026-10-12.csv). These are IPOPT `EXIT:` messages, not merely HTCondor job completion indicators.

**Finding:** For these paired conditions, measured-force-derived COP validity masks were strongly associated with successful numerical convergence. The result does **not** establish that every marker-derived case failed *because* of COP errors near heel strike/toe-off, nor that converged force-mask solutions had accurate joint mechanics or plausible motion.

## Scope and limitations

| Research question | Supported conclusion |
|---|---|
| Can our adapted walking setup run using laboratory inputs? | Yes; E009 ran and achieved optimal solver termination. |
| Did COP-mask choice affect numerical convergence under tested conditions? | Yes; 0/8 marker-based versus 8/8 force-based achieved optimal termination. |
| Were gait events determined by force measurements in the force-mask variant? | No. Gait events and stance percentages remained marker-derived. |
| Did we exactly reproduce Emily's published gait results? | Not established. |
| Were GRF/COP, kinematics, joint moments, and pelvis residuals quantitatively validated across eight subjects? | Not established. |
| Can the same force-derived mask be used directly for video-only motion capture? | No; it requires experimentally measured GRF or a separate contact-validity estimator. |

The 20 N threshold was a choice for the walking sensitivity test, not a universal contact threshold. Experimental force masks can be valuable in laboratory validation but introduce dependence on measured forces that would not necessarily be present in a video-only deployment.

## Relation to E056 and the STS study

- Our E008/E056 STS formulation uses a **separate force-derived COP mask at 10 N**, distinct from the walking study's 20 N mask.
- The STS E015–E086 factorial study varied whether the COP tracking and monotonic **objective terms** were enabled; **COP-mask method was held fixed**. It therefore does not independently test marker-versus-force masks for STS.
- The STS parameter study also held `heel_vGRF_threshold=0`, which **disables the separate minimum modeled heel-contact-force inequality**. That is not the COP-mask threshold.
- E056 remains a provisional numerical and force/COP-tracking baseline that requires quantitative biomechanical assessment, especially foot contact, pelvis residuals, joint kinematics, and inverse-dynamics consistency.

For context, see [STS formulation decisions](STS_formulation_decisions.md), [E056 selection](E056_selection_2026-11-08.md), and [new STS adaptation checklist](apply_E056_to_new_STS.md).

## Archived source and provenance

- [E009 walking runner](../source/opensimad_source_snapshot/runners/run_E009.py)
- [E111–E126 walking runner](../source/opensimad_source_snapshot/runners/run_walking_multi.py)
- [Walking experiment manifest](../source/opensimad_source_snapshot/metadata/walking_multi_manifest.json)
- [Per-ID walking outcomes](../data/walking_outcomes_transcribed_2026-10-12.csv)
- [Biomechanical validation and outstanding work](validation_and_next_steps.md)
- [CHTC job and source provenance](provenance.md)

No participant-specific time series, video, experimental force plate recordings, or full result archives should be committed to the public repository.
