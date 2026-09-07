// Fixed-timestep accumulator (deterministic simulation stepping, e.g. traffic at 20 Hz).
//
//   FixedStepClock clock(1.0 / 20.0);
//   int steps = clock.advance(frameDt);
//   for (int i = 0; i < steps; ++i) simulate(clock.step());
//   render(interpolate(previous, current, clock.alpha()));
#pragma once

#include <cstdint>

#include "nycsim/Config.h"

namespace nycsim {

class NYCSIM_API FixedStepClock {
 public:
  /// @param stepSeconds  fixed step (> 0)
  /// @param maxStepsPerAdvance  cap on steps returned by one advance(); excess time is dropped and
  ///        accounted in droppedSeconds() (prevents the spiral of death after a stall).
  explicit FixedStepClock(double stepSeconds = 1.0 / 20.0, int maxStepsPerAdvance = 8);

  /// Accumulates real time and returns the number of fixed steps the caller must run now.
  /// Negative or non-finite dt is treated as zero.
  int advance(double realDtSeconds);

  double step() const { return step_; }
  /// Fraction [0,1) of a step accumulated but not yet simulated (render interpolation factor).
  double alpha() const { return accumulator_ / step_; }
  uint64_t stepCount() const { return stepCount_; }
  /// Simulated time = stepCount * step (exact multiple of the step).
  double simTime() const { return static_cast<double>(stepCount_) * step_; }
  double droppedSeconds() const { return dropped_; }
  double accumulated() const { return accumulator_; }
  int maxStepsPerAdvance() const { return maxSteps_; }

  void reset();

 private:
  double step_;
  int maxSteps_;
  double accumulator_ = 0.0;
  double dropped_ = 0.0;
  uint64_t stepCount_ = 0;
};

}  // namespace nycsim
