#include "nycsim/vehicle/VehicleSpec.h"

namespace nycsim {
namespace vehicle {

const VehicleSpec& fusionHybrid2019() {
  // Function-local static: no dynamic initialisation at load time (the type is an aggregate of
  // scalars, so this is constant-initialised and thread-safe without a guard variable).
  static const VehicleSpec spec{};
  return spec;
}

}  // namespace vehicle
}  // namespace nycsim
