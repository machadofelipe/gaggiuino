#ifndef PROFILE_BUILDER_H
#define PROFILE_BUILDER_H

#include "profiling_phases.h"

struct ProfileBuildResult {
  Profile profile;
  int preInfusionFinishedPhaseIdx = 0;
};

ProfileBuildResult buildProfileFromConfig(const eepromValues_t& runningCfg);

#endif