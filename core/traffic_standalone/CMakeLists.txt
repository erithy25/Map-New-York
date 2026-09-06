# core/traffic_standalone — builds the traffic / routing / pedestrian lane on its
# own, so this lane can be compiled, tested and benchmarked while the rest of
# nycsim_core is under repair, and adds the benchmark executable to the normal
# build as well.
#
#   standalone:  cmake -S core/traffic_standalone -B build/traffic && cmake --build build/traffic
#                ./build/traffic/nycsim_traffic_tests      # doctest, all lane suites
#                ./build/traffic/nycsim_traffic_bench      # 5k vehicles + 20k peds @ 20 Hz
#   in-tree:     configured automatically by core/CMakeLists.txt (bench only —
#                the lane's sources and test suites are already in nycsim_core).
cmake_minimum_required(VERSION 3.20)

set(NYCSIM_LANE_SOURCES
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

set(NYCSIM_LANE_TESTS
  tests/routing/test_routing.cpp
  tests/traffic/test_models.cpp
  tests/traffic/test_signals.cpp
  tests/traffic/test_sim.cpp
  tests/peds/test_peds.cpp)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  # ---------------------------------------------------------------- standalone
  project(nycsim_traffic_lane VERSION 1.0.0 LANGUAGES CXX)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_CXX_EXTENSIONS OFF)
  if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
  endif()
  set(NYCSIM_CORE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
  set(NYCSIM_WARNINGS -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion
      -Wdouble-promotion -Wformat=2 -Wundef -Wcast-align -Werror)

  list(TRANSFORM NYCSIM_LANE_SOURCES PREPEND "${NYCSIM_CORE_ROOT}/")
  add_library(nycsim_lane STATIC ${NYCSIM_LANE_SOURCES})
  target_include_directories(nycsim_lane PUBLIC "${NYCSIM_CORE_ROOT}/include")
  target_compile_options(nycsim_lane PRIVATE ${NYCSIM_WARNINGS} -fno-exceptions -fno-rtti)
  set_target_properties(nycsim_lane PROPERTIES POSITION_INDEPENDENT_CODE ON)

  enable_testing()
  list(TRANSFORM NYCSIM_LANE_TESTS PREPEND "${NYCSIM_CORE_ROOT}/")
  add_executable(nycsim_traffic_tests test_main.cpp ${NYCSIM_LANE_TESTS})
  target_link_libraries(nycsim_traffic_tests PRIVATE nycsim_lane)
  target_include_directories(nycsim_traffic_tests SYSTEM PRIVATE "${NYCSIM_CORE_ROOT}/third_party")
  target_compile_options(nycsim_traffic_tests PRIVATE ${NYCSIM_WARNINGS})
  foreach(suite routing traffic peds)
    add_test(NAME ${suite} COMMAND nycsim_traffic_tests --test-suite=${suite} --no-intro=true)
    set_tests_properties(${suite} PROPERTIES TIMEOUT 900)
  endforeach()

  add_executable(nycsim_traffic_bench bench_main.cpp)
  target_link_libraries(nycsim_traffic_bench PRIVATE nycsim_lane)
  target_compile_options(nycsim_traffic_bench PRIVATE ${NYCSIM_WARNINGS})
else()
  # ------------------------------------------------- included from core/ build
  add_executable(nycsim_traffic_bench ${CMAKE_CURRENT_SOURCE_DIR}/bench_main.cpp)
  target_link_libraries(nycsim_traffic_bench PRIVATE nycsim_core)
  target_compile_options(nycsim_traffic_bench PRIVATE ${NYCSIM_WARNINGS})
endif()
