#include <unity.h>

#include "profile_builder.h"

namespace {

eepromValues_t buildConfig() {
  eepromValues_t cfg{};
  cfg.activeProfile = 0;
  return cfg;
}

eepromValues_t::profile_t& activeProfile(eepromValues_t& cfg) {
  return cfg.profiles[cfg.activeProfile];
}

}

void test_pressure_preinfusion_zero_flow_is_ignored(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).preinfusionState = true;
  activeProfile(cfg).preinfusionFlowState = false;
  activeProfile(cfg).preinfusionBar = 2.0f;
  activeProfile(cfg).preinfusionSec = 4;
  activeProfile(cfg).preinfusionPressureFlowTarget = 0.0f;

  ProfileBuildResult result = buildProfileFromConfig(cfg);

  TEST_ASSERT_EQUAL(2, result.profile.phaseCount());
  TEST_ASSERT_EQUAL(PHASE_TYPE::PHASE_TYPE_PRESSURE, result.profile.phases[0].type);
  TEST_ASSERT_EQUAL_FLOAT(-1.0f, result.profile.phases[0].restriction);
}

void test_flow_preinfusion_zero_pressure_is_ignored(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).preinfusionState = true;
  activeProfile(cfg).preinfusionFlowState = true;
  activeProfile(cfg).preinfusionFlowVol = 3.0f;
  activeProfile(cfg).preinfusionFlowTime = 4;
  activeProfile(cfg).preinfusionFlowPressureTarget = 0.0f;

  ProfileBuildResult result = buildProfileFromConfig(cfg);

  TEST_ASSERT_EQUAL(2, result.profile.phaseCount());
  TEST_ASSERT_EQUAL(PHASE_TYPE::PHASE_TYPE_FLOW, result.profile.phases[0].type);
  TEST_ASSERT_EQUAL_FLOAT(-1.0f, result.profile.phases[0].restriction);
}

void test_pressure_soak_zero_flow_is_ignored(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).soakState = true;
  activeProfile(cfg).soakTimePressure = 5;
  activeProfile(cfg).soakKeepPressure = 2.0f;
  activeProfile(cfg).soakKeepFlow = 0.0f;

  ProfileBuildResult result = buildProfileFromConfig(cfg);

  TEST_ASSERT_EQUAL(2, result.profile.phaseCount());
  TEST_ASSERT_EQUAL(PHASE_TYPE::PHASE_TYPE_PRESSURE, result.profile.phases[0].type);
  TEST_ASSERT_EQUAL_FLOAT(-1.0f, result.profile.phases[0].restriction);
}

void test_pressure_transition_zero_flow_is_ignored(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).profilingState = true;
  activeProfile(cfg).tpState = true;
  activeProfile(cfg).tpType = false;
  activeProfile(cfg).tpProfilingStart = 2.0f;
  activeProfile(cfg).tpProfilingFinish = 6.0f;
  activeProfile(cfg).tpProfilingSlope = 2;
  activeProfile(cfg).tpProfilingFlowRestriction = 0.0f;
  activeProfile(cfg).mpProfilingStart = 6.0f;
  activeProfile(cfg).mpProfilingFinish = 9.0f;
  activeProfile(cfg).mpProfilingSlope = 3;

  ProfileBuildResult result = buildProfileFromConfig(cfg);

  TEST_ASSERT_EQUAL_FLOAT(-1.0f, result.profile.phases[0].restriction);
}

void test_pressure_main_profile_zero_flow_is_ignored(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).profilingState = true;
  activeProfile(cfg).mfProfileState = false;
  activeProfile(cfg).mpProfilingStart = 6.0f;
  activeProfile(cfg).mpProfilingFinish = 9.0f;
  activeProfile(cfg).mpProfilingSlope = 3;
  activeProfile(cfg).mpProfilingFlowRestriction = 0.0f;

  ProfileBuildResult result = buildProfileFromConfig(cfg);

  TEST_ASSERT_EQUAL(1, result.profile.phaseCount());
  TEST_ASSERT_EQUAL_FLOAT(-1.0f, result.profile.phases[0].restriction);
}

void test_flow_transition_zero_pressure_is_ignored(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).profilingState = true;
  activeProfile(cfg).tpState = true;
  activeProfile(cfg).tpType = true;
  activeProfile(cfg).tfProfileStart = 2.0f;
  activeProfile(cfg).tfProfileEnd = 5.0f;
  activeProfile(cfg).tfProfileSlope = 2;
  activeProfile(cfg).tfProfilingPressureRestriction = 0.0f;
  activeProfile(cfg).mfProfileState = true;
  activeProfile(cfg).mfProfileStart = 5.0f;
  activeProfile(cfg).mfProfileEnd = 7.0f;
  activeProfile(cfg).mfProfileSlope = 3;

  ProfileBuildResult result = buildProfileFromConfig(cfg);

  TEST_ASSERT_EQUAL_FLOAT(-1.0f, result.profile.phases[0].restriction);
}

void test_flow_main_profile_zero_pressure_is_ignored(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).profilingState = true;
  activeProfile(cfg).mfProfileState = true;
  activeProfile(cfg).mfProfileStart = 3.0f;
  activeProfile(cfg).mfProfileEnd = 6.0f;
  activeProfile(cfg).mfProfileSlope = 2;
  activeProfile(cfg).mfProfilingPressureRestriction = 0.0f;

  ProfileBuildResult result = buildProfileFromConfig(cfg);

  TEST_ASSERT_EQUAL(1, result.profile.phaseCount());
  TEST_ASSERT_EQUAL_FLOAT(-1.0f, result.profile.phases[0].restriction);
}

void test_zero_start_pressure_transition_keeps_hold_phase(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).profilingState = true;
  activeProfile(cfg).tpState = true;
  activeProfile(cfg).tpType = false;
  activeProfile(cfg).tpProfilingStart = 0.0f;
  activeProfile(cfg).tpProfilingFinish = 6.0f;
  activeProfile(cfg).tpProfilingHold = 3;
  activeProfile(cfg).tpProfilingSlope = 2;
  activeProfile(cfg).tpProfilingSlopeShape = static_cast<uint16_t>(TransitionCurve::EASE_IN_OUT);
  activeProfile(cfg).mpProfilingStart = 6.0f;
  activeProfile(cfg).mpProfilingFinish = 9.0f;
  activeProfile(cfg).mpProfilingSlope = 3;

  ProfileBuildResult result = buildProfileFromConfig(cfg);

  TEST_ASSERT_EQUAL(3, result.profile.phaseCount());
  TEST_ASSERT_EQUAL(PHASE_TYPE::PHASE_TYPE_PRESSURE, result.profile.phases[0].type);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, result.profile.phases[0].target.end);
  TEST_ASSERT_EQUAL(3000, result.profile.phases[0].stopConditions.time);
}

void test_zero_start_flow_transition_keeps_hold_phase(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).profilingState = true;
  activeProfile(cfg).tpState = true;
  activeProfile(cfg).tpType = true;
  activeProfile(cfg).tfProfileStart = 0.0f;
  activeProfile(cfg).tfProfileEnd = 4.0f;
  activeProfile(cfg).tfProfileHold = 2;
  activeProfile(cfg).tfProfileSlope = 1;
  activeProfile(cfg).mfProfileState = true;
  activeProfile(cfg).mfProfileStart = 4.0f;
  activeProfile(cfg).mfProfileEnd = 6.0f;
  activeProfile(cfg).mfProfileSlope = 3;

  ProfileBuildResult result = buildProfileFromConfig(cfg);

  TEST_ASSERT_EQUAL(3, result.profile.phaseCount());
  TEST_ASSERT_EQUAL(PHASE_TYPE::PHASE_TYPE_FLOW, result.profile.phases[0].type);
  TEST_ASSERT_EQUAL_FLOAT(0.0f, result.profile.phases[0].target.end);
  TEST_ASSERT_EQUAL(2000, result.profile.phases[0].stopConditions.time);
}

void test_bar_profile_progression_preserves_hold_and_slope_shape(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).preinfusionState = true;
  activeProfile(cfg).preinfusionFlowState = false;
  activeProfile(cfg).preinfusionBar = 2.0f;
  activeProfile(cfg).preinfusionSec = 4;
  activeProfile(cfg).preinfusionPressureFlowTarget = 0.0f;

  activeProfile(cfg).soakState = true;
  activeProfile(cfg).soakTimePressure = 5;
  activeProfile(cfg).soakKeepPressure = 2.0f;
  activeProfile(cfg).soakKeepFlow = 0.0f;

  activeProfile(cfg).profilingState = true;
  activeProfile(cfg).tpState = true;
  activeProfile(cfg).tpType = false;
  activeProfile(cfg).tpProfilingStart = 3.0f;
  activeProfile(cfg).tpProfilingFinish = 6.0f;
  activeProfile(cfg).tpProfilingHold = 3;
  activeProfile(cfg).tpProfilingSlope = 2;
  activeProfile(cfg).tpProfilingSlopeShape = static_cast<uint16_t>(TransitionCurve::EASE_IN_OUT);
  activeProfile(cfg).tpProfilingFlowRestriction = 0.0f;

  activeProfile(cfg).mfProfileState = false;
  activeProfile(cfg).mpProfilingStart = 6.0f;
  activeProfile(cfg).mpProfilingFinish = 9.0f;
  activeProfile(cfg).mpProfilingSlope = 4;
  activeProfile(cfg).mpProfilingSlopeShape = static_cast<uint16_t>(TransitionCurve::LINEAR);
  activeProfile(cfg).mpProfilingFlowRestriction = 0.0f;

  ProfileBuildResult buildResult = buildProfileFromConfig(cfg);
  SensorState state{};
  PhaseProfiler profiler(buildResult.profile);

  TEST_ASSERT_EQUAL(2, buildResult.preInfusionFinishedPhaseIdx);

  profiler.updatePhase(0, state);
  TEST_ASSERT_EQUAL(0, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(2.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(4000, state);
  TEST_ASSERT_EQUAL(1, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(2.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(9000, state);
  TEST_ASSERT_EQUAL(2, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(3.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(10500, state);
  TEST_ASSERT_EQUAL(2, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(3.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(12000, state);
  TEST_ASSERT_EQUAL(3, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(3.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(13000, state);
  TEST_ASSERT_EQUAL(3, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(4.5f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(14000, state);
  TEST_ASSERT_EQUAL(4, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(6.0f, profiler.getCurrentPhase().getTarget());
}

void test_flow_profile_progression_preserves_hold_and_slope_shape(void) {
  eepromValues_t cfg = buildConfig();
  activeProfile(cfg).preinfusionState = true;
  activeProfile(cfg).preinfusionFlowState = true;
  activeProfile(cfg).preinfusionFlowVol = 2.0f;
  activeProfile(cfg).preinfusionFlowTime = 4;
  activeProfile(cfg).preinfusionFlowPressureTarget = 0.0f;

  activeProfile(cfg).soakState = true;
  activeProfile(cfg).soakTimeFlow = 3;
  activeProfile(cfg).soakKeepFlow = 2.0f;
  activeProfile(cfg).soakKeepPressure = 0.0f;

  activeProfile(cfg).profilingState = true;
  activeProfile(cfg).tpState = true;
  activeProfile(cfg).tpType = true;
  activeProfile(cfg).tfProfileStart = 1.0f;
  activeProfile(cfg).tfProfileEnd = 4.0f;
  activeProfile(cfg).tfProfileHold = 2;
  activeProfile(cfg).tfProfileSlope = 2;
  activeProfile(cfg).tfProfileSlopeShape = static_cast<uint16_t>(TransitionCurve::EASE_IN_OUT);
  activeProfile(cfg).tfProfilingPressureRestriction = 0.0f;

  activeProfile(cfg).mfProfileState = true;
  activeProfile(cfg).mfProfileStart = 4.0f;
  activeProfile(cfg).mfProfileEnd = 6.0f;
  activeProfile(cfg).mfProfileSlope = 3;
  activeProfile(cfg).mfProfileSlopeShape = static_cast<uint16_t>(TransitionCurve::LINEAR);
  activeProfile(cfg).mfProfilingPressureRestriction = 0.0f;

  ProfileBuildResult buildResult = buildProfileFromConfig(cfg);
  SensorState state{};
  PhaseProfiler profiler(buildResult.profile);

  TEST_ASSERT_EQUAL(2, buildResult.preInfusionFinishedPhaseIdx);

  profiler.updatePhase(0, state);
  TEST_ASSERT_EQUAL(0, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(2.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(4000, state);
  TEST_ASSERT_EQUAL(1, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(2.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(7000, state);
  TEST_ASSERT_EQUAL(2, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(1.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(8000, state);
  TEST_ASSERT_EQUAL(2, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(1.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(9000, state);
  TEST_ASSERT_EQUAL(3, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(1.0f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(10000, state);
  TEST_ASSERT_EQUAL(3, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(2.5f, profiler.getCurrentPhase().getTarget());

  profiler.updatePhase(11000, state);
  TEST_ASSERT_EQUAL(4, profiler.getCurrentPhase().getIndex());
  TEST_ASSERT_EQUAL_FLOAT(4.0f, profiler.getCurrentPhase().getTarget());
}

void runAllProfileBuilderTests(void) {
  RUN_TEST(test_pressure_preinfusion_zero_flow_is_ignored);
  RUN_TEST(test_flow_preinfusion_zero_pressure_is_ignored);
  RUN_TEST(test_pressure_soak_zero_flow_is_ignored);
  RUN_TEST(test_pressure_transition_zero_flow_is_ignored);
  RUN_TEST(test_pressure_main_profile_zero_flow_is_ignored);
  RUN_TEST(test_flow_transition_zero_pressure_is_ignored);
  RUN_TEST(test_flow_main_profile_zero_pressure_is_ignored);
  RUN_TEST(test_zero_start_pressure_transition_keeps_hold_phase);
  RUN_TEST(test_zero_start_flow_transition_keeps_hold_phase);
  RUN_TEST(test_bar_profile_progression_preserves_hold_and_slope_shape);
  RUN_TEST(test_flow_profile_progression_preserves_hold_and_slope_shape);
}