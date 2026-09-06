cmake_minimum_required(VERSION 3.20)
project(nycsim_core VERSION 1.0.0 LANGUAGES CXX)

# ---------------------------------------------------------------------------------------------------
# nycsim_core — engine-agnostic C++17 static library (geodesy, tiling/streaming, NYCB/JSON I/O,
# time zones, astronomy, weather, vehicle spec, utilities) plus the lanes owned by other agents
# (traffic, routing, peds) which hook in through optional per-lane CMake files.
#
# Unreal: the UE module (unreal/NYCSim/Source/NYCSimCore) compiles the same sources directly with
# UBT (see core/README.md); this CMake build is for standalone builds and the test suite.
# ---------------------------------------------------------------------------------------------------

option(NYCSIM_BUILD_TESTS "Build the doctest unit tests" ON)
option(NYCSIM_NO_EXCEPTIONS "Compile the library with -fno-exceptions -fno-rtti (mirrors Unreal)" ON)
option(NYCSIM_WERROR "Treat warnings as errors" ON)
option(NYCSIM_BUILD_LANES "Build the optional per-lane subdirectories (traffic/routing/peds)" ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(NYCSIM_WARNINGS)
if(MSVC)
  list(APPEND NYCSIM_WARNINGS /W4 /permissive-)
  if(NYCSIM_WERROR)
    list(APPEND NYCSIM_WARNINGS /WX)
  endif()
else()
  list(APPEND NYCSIM_WARNINGS -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion
       -Wdouble-promotion -Wformat=2 -Wundef -Wcast-align)
  if(NYCSIM_WERROR)
    list(APPEND NYCSIM_WARNINGS -Werror)
  endif()
endif()

# ---- library --------------------------------------------------------------------------------------
set(NYCSIM_CORE_SOURCES
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
  src/time/NyTime.cpp
  src/astro/Spa.cpp
  src/astro/Moon.cpp
  src/weather/WeatherState.cpp
  src/weather/NwsParser.cpp
  src/weather/OpenMeteoParser.cpp
  src/weather/MetarParser.cpp
  src/weather/WeatherService.cpp
  src/weather/WorldEffects.cpp
  src/vehicle/VehicleSpec.cpp
  src/vehicle/Friction.cpp
  src/vehicle/Powertrain.cpp
  src/vehicle/LongitudinalSim.cpp
)

add_library(nycsim_core STATIC ${NYCSIM_CORE_SOURCES})
add_library(nycsim::core ALIAS nycsim_core)
target_include_directories(nycsim_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_options(nycsim_core PRIVATE ${NYCSIM_WARNINGS})
target_compile_definitions(nycsim_core PUBLIC NYCSIM_API=)
if(NYCSIM_NO_EXCEPTIONS AND NOT MSVC)
  target_compile_options(nycsim_core PRIVATE -fno-exceptions -fno-rtti)
endif()
set_target_properties(nycsim_core PROPERTIES POSITION_INDEPENDENT_CODE ON)

# ---- tests ----------------------------------------------------------------------------------------
if(NYCSIM_BUILD_TESTS)
  enable_testing()
  add_library(nycsim_doctest INTERFACE)
  target_include_directories(nycsim_doctest SYSTEM INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/third_party)

  # One executable with all suites; each suite is registered as its own ctest so failures are
  # attributable per module. Other lanes call nycsim_add_test_suite(<suite> <sources...>).
  add_executable(nycsim_core_tests tests/main.cpp)
  target_link_libraries(nycsim_core_tests PRIVATE nycsim_core nycsim_doctest)
  target_compile_options(nycsim_core_tests PRIVATE ${NYCSIM_WARNINGS})
  target_include_directories(nycsim_core_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
  target_compile_definitions(nycsim_core_tests PRIVATE
    NYCSIM_TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/tests/data")

  function(nycsim_add_test_suite suite)
    target_sources(nycsim_core_tests PRIVATE ${ARGN})
    add_test(NAME ${suite} COMMAND nycsim_core_tests --test-suite=${suite} --no-intro=true)
    set_tests_properties(${suite} PROPERTIES TIMEOUT 600)
  endfunction()

  nycsim_add_test_suite(util tests/util/test_util.cpp)
  nycsim_add_test_suite(geo tests/geo/test_geo.cpp)
  nycsim_add_test_suite(tiling tests/tiling/test_tile.cpp tests/tiling/test_scheduler.cpp)
  nycsim_add_test_suite(io tests/io/test_nycb.cpp tests/io/test_json.cpp)
  nycsim_add_test_suite(time tests/time/test_nytime.cpp)
  nycsim_add_test_suite(astro tests/astro/test_spa.cpp tests/astro/test_moon.cpp)
  nycsim_add_test_suite(weather tests/weather/test_parsers.cpp tests/weather/test_service.cpp
                        tests/weather/test_world_effects.cpp)
  nycsim_add_test_suite(vehicle tests/vehicle/test_vehicle.cpp)
endif()

# ---- other lanes (traffic / routing / peds agent) -------------------------------------------------
# Each lane may provide core/src/<lane>/CMakeLists.txt which typically calls
#   target_sources(nycsim_core PRIVATE <lane sources>)
#   nycsim_add_test_suite(<lane> tests/<lane>/*.cpp)
if(NYCSIM_BUILD_LANES)
  foreach(lane traffic routing peds)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/src/${lane}/CMakeLists.txt")
      add_subdirectory("src/${lane}")
    endif()
  endforeach()
endif()
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/traffic_standalone/CMakeLists.txt")
  add_subdirectory(traffic_standalone)
endif()

# ---- install --------------------------------------------------------------------------------------
include(GNUInstallDirs)
install(TARGETS nycsim_core ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
