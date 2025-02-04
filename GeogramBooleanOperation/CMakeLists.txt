set(MODULE_NAME GeogramBooleanOperation)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${CMAKE_CURRENT_SOURCE_DIR})

# Set the directory containing FindGeogram.cmake
set(GEOGRAM_CMAKE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/CMake")

# Prepend the directory to CMAKE_MODULE_PATH
list(PREPEND CMAKE_MODULE_PATH "${GEOGRAM_CMAKE_DIR}")

find_package(Geogram REQUIRED)

# Add the Geogram include directories
#include_directories(${GEOGRAM_INCLUDE_DIR})

#aux_source_directories(SOURCES "" .)
#vor_add_executable(${APP_NAME} ${SOURCES})

#-----------------------------------------------------------------------------

#
# SlicerExecutionModel
#
find_package(SlicerExecutionModel REQUIRED)
include(${SlicerExecutionModel_USE_FILE})

#-----------------------------------------------------------------------------
SEMMacroBuildCLI(
  NAME ${MODULE_NAME}
  LOGO_HEADER ${Slicer_SOURCE_DIR}/Resources/NAMICLogo.h
  TARGET_LIBRARIES ${VTK_LIBRARIES} MRMLCore Geogram::geogram
  INCLUDE_DIRECTORIES
    ${MRMLCore_INCLUDE_DIRS}
  )

#-----------------------------------------------------------------------------
#if(BUILD_TESTING)
#  add_subdirectory(Testing)
#endif()