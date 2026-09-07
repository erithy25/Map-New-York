# traffic lane — fleet, signals, density, synthetic grid, IDM/MOBIL agents.
target_sources(nycsim_core PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/VehicleClass.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/Signals.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/Density.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/SyntheticGrid.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/BusRoutes.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/TrafficSim.cpp)
if(NYCSIM_BUILD_TESTS)
  nycsim_add_test_suite(traffic
    ${PROJECT_SOURCE_DIR}/tests/traffic/test_models.cpp
    ${PROJECT_SOURCE_DIR}/tests/traffic/test_signals.cpp
    ${PROJECT_SOURCE_DIR}/tests/traffic/test_sim.cpp)
endif()
