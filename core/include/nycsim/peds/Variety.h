#pragma once
// nycsim/peds/Variety.h — the 12-dimensional appearance vector every crowd
// agent carries.  It is the contract between this simulation and the Blender
// NPC generator (blender/character/*): the C++ side draws the vector, the
// generator consumes exactly these twelve dimensions in this order, and the
// Unreal character component reads them off the agent to pick meshes, morph
// targets and material parameters.
//
// Each dimension is a float in [0,1] plus a documented number of quantization
// levels.  The quantized tuple is packed into a 64-bit `signature` in
// mixed-radix order, which is what the "no duplicates within 60 m" rule
// compares (ARCHITECTURE §10).  The total number of distinguishable
// appearances is the product of the level counts below — 6.4 × 10^10 — so a
// re-draw on collision terminates immediately in practice.
//
//   dim  name            levels  meaning / generator use
//   0    age_band         4      child / young adult / adult / senior
//   1    stature          6      height 1.50–1.95 m (dim → linear interpolation)
//   2    body_mass        6      slim → heavy body morph
//   3    skin_tone        8      Fitzpatrick-like ramp for the skin shader
//   4    hair_style      10      mesh id in the generator's hair library
//   5    hair_colour      8      colour ramp lookup
//   6    top_garment     10      jacket / coat / shirt / hoodie / uniform mesh
//   7    top_colour      12      palette index
//   8    bottom_garment   8      trousers / skirt / shorts / dress mesh
//   9    bottom_colour   12      palette index
//   10   footwear         6      shoe mesh id
//   11   accessory       10      none / bag / backpack / umbrella / headphones /
//                                hat / stroller / coffee / phone / dog
//
// Everything is deterministic: the vector is a pure function of the agent's
// Rng stream, so a seed reproduces the whole crowd exactly.

#include <cstdint>

#include "nycsim/traffic/Random.h"

namespace nycsim {
namespace peds {

constexpr uint32_t kVarietyDims = 12;

// Quantization levels, in dimension order.
constexpr uint8_t kVarietyLevels[kVarietyDims] = {4, 6, 6, 8, 10, 8, 10, 12, 8, 12, 6, 10};

// Names, in dimension order (for the report, the debug HUD and the glTF extras
// the Blender generator writes).
inline const char* varietyName(uint32_t dim) {
  static const char* kNames[kVarietyDims] = {"age_band",   "stature",     "body_mass",  "skin_tone",
                                             "hair_style", "hair_colour", "top_garment", "top_colour",
                                             "bottom_garment", "bottom_colour", "footwear", "accessory"};
  return dim < kVarietyDims ? kNames[dim] : "";
}

struct VarietyVector {
  float v[kVarietyDims] = {0.f};

  uint8_t level(uint32_t dim) const {
    const uint32_t n = kVarietyLevels[dim];
    float x = v[dim];
    if (x < 0.f) x = 0.f;
    if (x > 0.99999f) x = 0.99999f;
    return static_cast<uint8_t>(x * static_cast<float>(n));
  }
  // Mixed-radix packing of the quantized tuple.
  uint64_t signature() const {
    uint64_t sig = 0;
    for (uint32_t d = 0; d < kVarietyDims; ++d) sig = sig * kVarietyLevels[d] + level(d);
    return sig;
  }
  // Metric height in metres (dimension 1 mapped onto the NYC adult range,
  // shortened for the child band).
  float heightMetres() const {
    const float base = 1.50f + v[1] * 0.45f;
    return v[0] < 0.25f ? base * 0.72f : base;
  }
};

// Draws a uniform vector; every dimension is independent so the generator can
// vary one axis at a time when debugging.
inline VarietyVector drawVariety(Rng& rng) {
  VarietyVector out;
  for (uint32_t d = 0; d < kVarietyDims; ++d) out.v[d] = rng.uniform();
  return out;
}

}  // namespace peds
}  // namespace nycsim
