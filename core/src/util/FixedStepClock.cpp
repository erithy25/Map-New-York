#include "nycsim/util/FixedStepClock.h"

#include <cmath>

namespace nycsim {

FixedStepClock::FixedStepClock(double stepSeconds, int maxStepsPerAdvance)
    : step_(stepSeconds > 0.0 && std::isfinite(stepSeconds) ? stepSeconds : 1.0 / 20.0),
      maxSteps_(maxStepsPerAdvance < 1 ? 1 : maxStepsPerAdvance) {}

int FixedStepClock::advance(double realDtSeconds) {
  if (!(realDtSeconds > 0.0) || !std::isfinite(realDtSeconds)) realDtSeconds = 0.0;
  accumulator_ += realDtSeconds;
  int steps = 0;
  while (accumulator_ >= step_ && steps < maxSteps_) {
    accumulator_ -= step_;
    ++steps;
  }
  if (accumulator_ >= step_) {
    // Too far behind: drop the excess whole steps, keep the fractional remainder.
    const double excessSteps = std::floor(accumulator_ / step_);
    dropped_ += excessSteps * step_;
    accumulator_ -= excessSteps * step_;
  }
  stepCount_ += static_cast<uint64_t>(steps);
  return steps;
}

void FixedStepClock::reset() {
  accumulator_ = 0.0;
  dropped_ = 0.0;
  stepCount_ = 0;
}

}  // namespace nycsim
