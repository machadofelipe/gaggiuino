#include "profile_builder.h"

namespace {

float optionalRestriction(float value) {
  return value > 0.f ? value : -1.f;
}

void addPhase(Profile& profile, PHASE_TYPE type, Transition target, float restriction, int timeMs, float pressureAbove, float pressureBelow, float shotWeight, float isWaterPumped) {
  profile.addPhase(Phase {
    .type           = type,
    .target         = target,
    .restriction    = restriction,
    .stopConditions = PhaseStopConditions{ .time=timeMs, .pressureAbove=pressureAbove, .pressureBelow=pressureBelow, .weight=shotWeight, .waterPumpedInPhase=isWaterPumped }
  });
}

void addPressurePhase(Profile& profile, Transition pressure, float flowRestriction, int timeMs, float pressureAbove, float pressureBelow, float shotWeight, float isWaterPumped) {
  addPhase(profile, PHASE_TYPE::PHASE_TYPE_PRESSURE, pressure, flowRestriction, timeMs, pressureAbove, pressureBelow, shotWeight, isWaterPumped);
}

void addFlowPhase(Profile& profile, Transition flow, float pressureRestriction, int timeMs, float pressureAbove, float pressureBelow, float shotWeight, float isWaterPumped) {
  addPhase(profile, PHASE_TYPE::PHASE_TYPE_FLOW, flow, pressureRestriction, timeMs, pressureAbove, pressureBelow, shotWeight, isWaterPumped);
}

void addFillBasketPhase(Profile& profile, float flowRate) {
  addFlowPhase(profile, Transition(flowRate), -1, -1, 0.1f, -1, -1, -1);
}

void addPreinfusionPhases(Profile& profile, const eepromValues_t& runningCfg) {
  if (ACTIVE_PROFILE(runningCfg).preinfusionFlowState) {
    float isPressureAbove = ACTIVE_PROFILE(runningCfg).preinfusionPressureAbove ? ACTIVE_PROFILE(runningCfg).preinfusionFlowPressureTarget : -1.f;
    float isWeightAbove = ACTIVE_PROFILE(runningCfg).preinfusionWeightAbove > 0.f ? ACTIVE_PROFILE(runningCfg).preinfusionWeightAbove : -1.f;
    float isWaterPumped = ACTIVE_PROFILE(runningCfg).preinfusionFilled > 0.f ? ACTIVE_PROFILE(runningCfg).preinfusionFilled : -1.f;

    addFlowPhase(profile, Transition{ ACTIVE_PROFILE(runningCfg).preinfusionFlowVol }, optionalRestriction(ACTIVE_PROFILE(runningCfg).preinfusionFlowPressureTarget), ACTIVE_PROFILE(runningCfg).preinfusionFlowTime * 1000, isPressureAbove, -1, isWeightAbove, isWaterPumped);
  }
  else {
    float isPressureAbove = ACTIVE_PROFILE(runningCfg).preinfusionPressureAbove ? ACTIVE_PROFILE(runningCfg).preinfusionBar : -1.f;
    float isWeightAbove = ACTIVE_PROFILE(runningCfg).preinfusionWeightAbove > 0.f ? ACTIVE_PROFILE(runningCfg).preinfusionWeightAbove : -1.f;
    float isWaterPumped = ACTIVE_PROFILE(runningCfg).preinfusionFilled > 0.f ? ACTIVE_PROFILE(runningCfg).preinfusionFilled : -1.f;

    addPressurePhase(profile, Transition{ ACTIVE_PROFILE(runningCfg).preinfusionBar }, optionalRestriction(ACTIVE_PROFILE(runningCfg).preinfusionPressureFlowTarget), ACTIVE_PROFILE(runningCfg).preinfusionSec * 1000, isPressureAbove, -1, isWeightAbove, isWaterPumped);
  }
}

void addSoakPhase(Profile& profile, const eepromValues_t& runningCfg) {
  uint16_t phaseSoak = ACTIVE_PROFILE(runningCfg).preinfusionFlowState ? ACTIVE_PROFILE(runningCfg).soakTimeFlow : ACTIVE_PROFILE(runningCfg).soakTimePressure;
  float maintainFlow = ACTIVE_PROFILE(runningCfg).soakKeepFlow > 0.f ? ACTIVE_PROFILE(runningCfg).soakKeepFlow : -1.f;
  float maintainPressure = ACTIVE_PROFILE(runningCfg).soakKeepPressure > 0.f ? ACTIVE_PROFILE(runningCfg).soakKeepPressure : -1.f;
  float isPressureBelow = ACTIVE_PROFILE(runningCfg).soakBelowPressure > 0.f ? ACTIVE_PROFILE(runningCfg).soakBelowPressure : -1.f;
  float isPressureAbove = ACTIVE_PROFILE(runningCfg).soakAbovePressure > 0.f ? ACTIVE_PROFILE(runningCfg).soakAbovePressure : -1.f;
  float isWeightAbove = ACTIVE_PROFILE(runningCfg).soakAboveWeight > 0.f ? ACTIVE_PROFILE(runningCfg).soakAboveWeight : -1.f;

  if (maintainPressure > 0.f) {
    addPressurePhase(profile, Transition{maintainPressure}, optionalRestriction(maintainFlow), phaseSoak * 1000, isPressureAbove, isPressureBelow, isWeightAbove, -1);
  }
  else if (maintainFlow > 0.f) {
    addFlowPhase(profile, Transition{maintainFlow}, -1, phaseSoak * 1000, isPressureAbove, isPressureBelow, isWeightAbove, -1);
  }
  else {
    addPressurePhase(profile, Transition{maintainPressure}, maintainFlow, phaseSoak * 1000, isPressureAbove, isPressureBelow, isWeightAbove, -1);
  }
}

void insertRampPhaseIfNeeded(Profile& profile, const eepromValues_t& runningCfg, size_t rampPhaseIndex) {
  uint16_t rampTime = ACTIVE_PROFILE(runningCfg).preinfusionRamp;
  TransitionCurve rampCurve = (TransitionCurve)ACTIVE_PROFILE(runningCfg).preinfusionRampSlope;

  if (rampPhaseIndex <= 0 || rampTime <= 0 || rampCurve == TransitionCurve::INSTANT) {
    return;
  }

  Phase targetPhase = profile.phases[rampPhaseIndex];
  float targetValue = targetPhase.target.isInstant() ? targetPhase.target.end : targetPhase.target.start;

  if (targetValue <= 0) {
    return;
  }

  profile.insertPhase(Phase {
    .type           = targetPhase.type,
    .target         = Transition(targetValue, rampCurve, rampTime * 1000),
    .restriction    = -1,
    .stopConditions = PhaseStopConditions{ .time=rampTime * 1000 }
  }, rampPhaseIndex);
}

void addMainExtractionPhasesAndRamp(Profile& profile, const eepromValues_t& runningCfg) {
  int rampPhaseIndex = -1;

  if (ACTIVE_PROFILE(runningCfg).profilingState) {
    if (ACTIVE_PROFILE(runningCfg).tpState) {
      if (ACTIVE_PROFILE(runningCfg).tpType) {
        float fpStart = ACTIVE_PROFILE(runningCfg).tfProfileStart;
        float fpEnd = ACTIVE_PROFILE(runningCfg).tfProfileEnd;
        uint16_t fpHold = ACTIVE_PROFILE(runningCfg).tfProfileHold * 1000;
        float holdLimit = ACTIVE_PROFILE(runningCfg).tfProfileHoldLimit > 0.f ? ACTIVE_PROFILE(runningCfg).tfProfileHoldLimit : -1;
        TransitionCurve curve = (TransitionCurve)ACTIVE_PROFILE(runningCfg).tfProfileSlopeShape;
        uint16_t curveTime = ACTIVE_PROFILE(runningCfg).tfProfileSlope * 1000;

        if (fpStart >= 0.f && fpHold > 0) {
          addFlowPhase(profile, Transition{ fpStart }, holdLimit, fpHold, -1, -1, -1, -1);
          rampPhaseIndex = rampPhaseIndex > 0 ? rampPhaseIndex : profile.phaseCount() - 1;
        }
        addFlowPhase(profile, Transition{ fpStart, fpEnd, curve, curveTime }, optionalRestriction(ACTIVE_PROFILE(runningCfg).tfProfilingPressureRestriction), curveTime, -1, -1, -1, -1);
        rampPhaseIndex = rampPhaseIndex > 0 ? rampPhaseIndex : profile.phaseCount() - 1;
      }
      else {
        float ppStart = ACTIVE_PROFILE(runningCfg).tpProfilingStart;
        float ppEnd = ACTIVE_PROFILE(runningCfg).tpProfilingFinish;
        uint16_t ppHold = ACTIVE_PROFILE(runningCfg).tpProfilingHold * 1000;
        float holdLimit = ACTIVE_PROFILE(runningCfg).tpProfilingHoldLimit > 0.f ? ACTIVE_PROFILE(runningCfg).tpProfilingHoldLimit : -1;
        TransitionCurve curve = (TransitionCurve)ACTIVE_PROFILE(runningCfg).tpProfilingSlopeShape;
        uint16_t curveTime = ACTIVE_PROFILE(runningCfg).tpProfilingSlope * 1000;

        if (ppStart >= 0.f && ppHold > 0) {
          addPressurePhase(profile, Transition{ ppStart }, holdLimit, ppHold, -1, -1, -1, -1);
          rampPhaseIndex = rampPhaseIndex > 0 ? rampPhaseIndex : profile.phaseCount() - 1;
        }
        addPressurePhase(profile, Transition{ ppStart, ppEnd, curve, curveTime }, optionalRestriction(ACTIVE_PROFILE(runningCfg).tpProfilingFlowRestriction), curveTime, -1, -1, -1, -1);
        rampPhaseIndex = rampPhaseIndex > 0 ? rampPhaseIndex : profile.phaseCount() - 1;
      }
    }

    if (ACTIVE_PROFILE(runningCfg).mfProfileState) {
      float fpStart = ACTIVE_PROFILE(runningCfg).mfProfileStart;
      float fpEnd = ACTIVE_PROFILE(runningCfg).mfProfileEnd;
      TransitionCurve curve = (TransitionCurve)ACTIVE_PROFILE(runningCfg).mfProfileSlopeShape;
      uint16_t curveTime = ACTIVE_PROFILE(runningCfg).mfProfileSlope * 1000;

      addFlowPhase(profile, Transition(fpStart, fpEnd, curve, curveTime), optionalRestriction(ACTIVE_PROFILE(runningCfg).mfProfilingPressureRestriction), -1, -1, -1, -1, -1);
    }
    else {
      float ppStart = ACTIVE_PROFILE(runningCfg).mpProfilingStart;
      float ppEnd = ACTIVE_PROFILE(runningCfg).mpProfilingFinish;
      TransitionCurve curve = (TransitionCurve)ACTIVE_PROFILE(runningCfg).mpProfilingSlopeShape;
      uint16_t curveTime = ACTIVE_PROFILE(runningCfg).mpProfilingSlope * 1000;

      addPressurePhase(profile, Transition(ppStart, ppEnd, curve, curveTime), optionalRestriction(ACTIVE_PROFILE(runningCfg).mpProfilingFlowRestriction), -1, -1, -1, -1, -1);
    }
  }
  else {
    addPressurePhase(profile, Transition(9.f), -1, -1, -1, -1, -1, -1);
  }

  rampPhaseIndex = rampPhaseIndex > 0 ? rampPhaseIndex : profile.phaseCount() - 1;
  insertRampPhaseIfNeeded(profile, runningCfg, rampPhaseIndex);
}

}

ProfileBuildResult buildProfileFromConfig(const eepromValues_t& runningCfg) {
  ProfileBuildResult result;
  float shotTarget = -1.f;

  if (ACTIVE_PROFILE(runningCfg).stopOnWeightState) {
    shotTarget = (ACTIVE_PROFILE(runningCfg).shotStopOnCustomWeight < 1.f)
      ? ACTIVE_PROFILE(runningCfg).shotDose * ACTIVE_PROFILE(runningCfg).shotPreset
      : ACTIVE_PROFILE(runningCfg).shotStopOnCustomWeight;
  }

  result.profile.globalStopConditions = GlobalStopConditions{ .weight=shotTarget };

  if (runningCfg.basketPrefill) {
    addFillBasketPhase(result.profile, 7.f);
  }

  if (ACTIVE_PROFILE(runningCfg).preinfusionState) {
    addPreinfusionPhases(result.profile, runningCfg);
  }

  if (ACTIVE_PROFILE(runningCfg).soakState) {
    addSoakPhase(result.profile, runningCfg);
  }

  result.preInfusionFinishedPhaseIdx = result.profile.phaseCount();
  addMainExtractionPhasesAndRamp(result.profile, runningCfg);
  return result;
}