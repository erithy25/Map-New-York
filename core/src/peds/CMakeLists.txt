# pedestrian lane — sidewalk graph and social-force crowd.
target_sources(nycsim_core PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/SidewalkGraph.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/PedSim.cpp)
if(NYCSIM_BUILD_TESTS)
  nycsim_add_test_suite(peds ${PROJECT_SOURCE_DIR}/tests/peds/test_peds.cpp)
endif()
