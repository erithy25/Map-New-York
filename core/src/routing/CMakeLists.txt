# routing lane — lane-level graph and ALT router (traffic/routing/peds agent).
target_sources(nycsim_core PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/RoadGraph.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/Router.cpp)
if(NYCSIM_BUILD_TESTS)
  nycsim_add_test_suite(routing ${PROJECT_SOURCE_DIR}/tests/routing/test_routing.cpp)
endif()
