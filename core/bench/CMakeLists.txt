# core/bench — the performance and robustness benchmarks
# (docs/verification/performance/REPORT.md).
#
# Standalone, so it can be configured and built without touching core's own
# CMakeLists (which belongs to the foundation):
#
#   cmake -S core/bench -B core/build/bench -DCMAKE_BUILD_TYPE=Release
#   cmake --build core/build/bench -j2
#   ./core/build/bench/nycsim_bench synthetic
#
# core/build/ is git-ignored, so the binaries stay out of the repository.
#
# It also works when added from core/CMakeLists.txt with add_subdirectory(bench),
# in which case it links the already-built nycsim_core instead of compiling its
# own copy of the sources.
cmake_minimum_required(VERSION 3.20)

set(NYCSIM_BENCH_SOURCES
  bench_main.cpp
  bench_world.cpp
  bench_step.cpp
  bench_signals.cpp
  bench_stream.cpp)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  # ---------------------------------------------------------------- standalone
  project(nycsim_bench VERSION 1.0.0 LANGUAGES CXX)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_CXX_EXTENSIONS OFF)
  if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
  endif()
  set(NYCSIM_CORE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
  set(NYCSIM_WARNINGS -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion
      -Wdouble-promotion -Wformat=2 -Wundef -Wcast-align -Werror)

  # The subset of nycsim_core the benchmarks touch: utilities, geodesy, tiling,
  # NYCB/JSON I/O, routing, traffic and pedestrians.  Time, astronomy, weather
  # and the vehicle dynamics are not on any measured path.
  set(NYCSIM_BENCH_LIB_SOURCES
    src/util/Config.cpp
    src/util/Error.cpp
    src/util/Arena.cpp
    src/util/FixedStepClock.cpp
    src/util/Log.cpp
    src/geo/TransverseMercator.cpp
    src/geo/LambertConformalConic.cpp
    src/geo/NycTm.cpp
    src/geo/StatePlaneLI.cpp
    src/tiling/Tile.cpp
    src/tiling/TileScheduler.cpp
    src/tiling/TileCatalog.cpp
    src/io/Nycb.cpp
    src/io/Json.cpp
    src/routing/RoadGraph.cpp
    src/routing/Router.cpp
    src/traffic/VehicleClass.cpp
    src/traffic/Signals.cpp
    src/traffic/Density.cpp
    src/traffic/SyntheticGrid.cpp
    src/traffic/BusRoutes.cpp
    src/traffic/TrafficSim.cpp
    src/peds/SidewalkGraph.cpp
    src/peds/PedSim.cpp)
  list(TRANSFORM NYCSIM_BENCH_LIB_SOURCES PREPEND "${NYCSIM_CORE_ROOT}/")

  add_library(nycsim_bench_core STATIC ${NYCSIM_BENCH_LIB_SOURCES})
  target_include_directories(nycsim_bench_core PUBLIC "${NYCSIM_CORE_ROOT}/include")
  target_compile_definitions(nycsim_bench_core PUBLIC NYCSIM_API=)
  target_compile_options(nycsim_bench_core PRIVATE ${NYCSIM_WARNINGS} -fno-exceptions -fno-rtti)
  set_target_properties(nycsim_bench_core PROPERTIES POSITION_INDEPENDENT_CODE ON)

  add_executable(nycsim_bench ${NYCSIM_BENCH_SOURCES})
  target_link_libraries(nycsim_bench PRIVATE nycsim_bench_core)
  target_compile_options(nycsim_bench PRIVATE ${NYCSIM_WARNINGS} -fno-exceptions -fno-rtti)
else()
  # ------------------------------------------------- included from core/build
  add_executable(nycsim_bench ${NYCSIM_BENCH_SOURCES})
  target_link_libraries(nycsim_bench PRIVATE nycsim_core)
  target_compile_options(nycsim_bench PRIVATE ${NYCSIM_WARNINGS})
endif()
