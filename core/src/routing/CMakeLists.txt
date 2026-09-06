# Routing lane: road graph + router. Owned jointly with the traffic agent (which may extend the
# graph); the sources are attached to nycsim_core here so the library always links a routing lane.
target_sources(nycsim_core PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/RoadGraph.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/Router.cpp)
if(NYCSIM_BUILD_TESTS AND EXISTS "${CMAKE_SOURCE_DIR}/tests/routing/test_routing.cpp")
  nycsim_add_test_suite(routing ${CMAKE_SOURCE_DIR}/tests/routing/test_routing.cpp)
endif()
