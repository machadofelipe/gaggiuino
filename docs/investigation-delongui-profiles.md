# Delongui Profile Investigation

Date: 2026-05-05

## Scope

This investigation targeted profile behavior for the `delongui-51mm-forced-predictive-stlink` environment, with emphasis on the configuration family you described:

- BAR-controlled phases across PI, Soak, Soak->Profile, and Profile
- inactive flow settings set to `0`
- hold times and slope times configured
- slope shape expected to affect the trajectory
- predictive scales forced on

The goal was to reproduce the profile-construction and phase-progression behavior in native tests, confirm root causes, fix confirmed defects, and verify the firmware still builds for the Delongui preset.

## Expected Semantics Locked For This Pass

- An explicit phase start of `0` is a real configured value, not an instruction to fall back to the live sensor snapshot.
- If a phase is enabled and its hold time is non-zero, that hold must still exist even when the phase starts at `0`.
- In BAR-controlled phases, a flow setting of `0` means "ignore the flow axis", not "enforce a zero-flow restriction".
- In FLOW-controlled phases, a pressure setting of `0` means "ignore the pressure axis", not "enforce a zero-pressure restriction".
- Slope shape must be observable in sampled targets, not only in the final endpoint.

## Confirmed Root Causes

### 1. Explicit zero starts were treated as "unset"

File: `lib/Common/profiling_phases.cpp`

`Phase::getTarget()` used `target.start > 0.f` to decide whether a configured start existed. That caused an explicit `0` start to be replaced with the live pressure or flow snapshot. The result was that zero-start ramps began from the current sensor value instead of from zero.

Impact:

- zero-start hold/ramp phases produced incorrect starting targets
- curve sampling could look wrong even when the configured curve type was valid
- pressure and flow behavior diverged from the configured profile whenever the start value was `0`

### 2. Inactive-axis zeros were emitted as real restrictions

Files:

- `src/gaggiuino.ino` before extraction
- `lib/Common/profile_builder.cpp` after extraction/fix

Pressure-based PI, Transition Profile, and Main Profile passed `0` directly as a flow restriction. Flow-based PI, Transition Profile, and Main Profile did the symmetric thing with pressure restrictions. Pressure-based soak also substituted a hard-coded `2.5f` flow restriction when only a pressure target was configured.

Impact:

- BAR-only configurations with flow left at `0` still applied a flow restriction
- soak could silently clamp to `2.5f` instead of ignoring flow
- this could distort the apparent timing and shape of later transitions

### 3. Zero-start transition holds were skipped entirely

Files:

- `src/gaggiuino.ino` before extraction
- `lib/Common/profile_builder.cpp` after extraction/fix

Transition hold phases were only added when `start > 0`. A valid start value of `0` therefore removed the hold phase from the built profile.

Impact:

- configured hold time was lost
- the next slope began immediately
- observed behavior could look like hold time and slope time were being mixed up

## Fixes Applied

### Runtime and profile-construction changes

- Added `lib/Common/profile_builder.h` and `lib/Common/profile_builder.cpp` to hold profile construction in one testable place.
- Updated `src/gaggiuino.ino` to build runtime phases through `buildProfileFromConfig(runningCfg)`.
- Removed the old duplicate builder block from `src/gaggiuino.ino` so the extracted helper is now the only behavior source.
- Changed `Phase::getTarget()` to treat `start >= 0` as an explicit configured start.
- Normalized inactive-axis restrictions so `0` becomes `-1` (ignored) instead of a literal restriction.
- Changed transition hold insertion checks from `> 0` to `>= 0` so zero-start holds are retained.

## Tests Added

### Low-level interpolation tests

Added to `test/tests/test_pressure_profiler.cpp`:

- explicit zero-start pressure ramp uses zero, not snapshot pressure
- explicit zero-start flow ramp uses zero, not snapshot flow
- non-instant curve sampling (`EASE_IN_OUT`) still respects explicit zero starts

### Builder and profile-matrix tests

Added to `test/tests/test_profile_builder.cpp`:

- pressure PI ignores zero flow restriction
- flow PI ignores zero pressure restriction
- pressure soak ignores zero flow restriction
- pressure transition ignores zero flow restriction
- pressure main profile ignores zero flow restriction
- flow transition ignores zero pressure restriction
- flow main profile ignores zero pressure restriction
- zero-start pressure transition retains hold phase
- zero-start flow transition retains hold phase
- representative BAR progression test for PI -> Soak -> Transition Hold -> Transition Slope -> Main Profile
- representative FLOW progression test for PI -> Soak -> Transition Hold -> Transition Slope -> Main Profile

## Validation Results

### Native test suite

Command:

```sh
~/.platformio/penv/bin/pio test -e test
```

Result:

- `25` test cases passed
- `0` test cases failed

### Delongui target build

Command:

```sh
~/.platformio/penv/bin/pio run -e delongui-51mm-forced-predictive-stlink
```

Result:

- build succeeded
- memory summary: RAM `22.0%`, Flash `25.0%`

## Files Changed

- `lib/Common/profiling_phases.cpp`
- `lib/Common/profile_builder.h`
- `lib/Common/profile_builder.cpp`
- `src/gaggiuino.ino`
- `test/tests/test_pressure_profiler.cpp`
- `test/tests/test_profile_builder.cpp`
- `test/test_main.cpp`

## Residual Risks And Follow-Up Notes

- This pass covered the meaningful mode combinations and representative value classes, not every continuous numeric value.
- Preinfusion-ramp insertion edge cases around ramp target index selection and ramping to zero-valued targets were not expanded into dedicated regression tests in this pass.
- Predictive-scales math itself was not rewritten here; the new tests validate profile construction and phase progression under representative inputs, but not the full physics of predictive output estimation on machine.
- The Delongui build still reports three existing unused-function warnings in `src/gaggiuino.ino` related to boiler-fill helpers. They predate this profile fix and were not changed as part of this work.

## Practical Outcome

For the investigated profile paths, the firmware now:

- honors explicit zero-start ramps
- preserves hold phases even when the start value is zero
- ignores inactive-axis zero values instead of treating them as real restrictions
- preserves sampled slope behavior for both BAR and FLOW profile progressions
