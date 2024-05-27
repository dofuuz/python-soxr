cmake_minimum_required(VERSION 3.15...3.26)

project(nanobind_example LANGUAGES CXX)

if (NOT SKBUILD)
    message(WARNING "\
    This CMake file is meant to be executed using 'scikit-build'. Running
    it directly will almost certainly not produce the desired result. If
    you are a user trying to install this package, please use the command
    below, which will install all necessary build dependencies, compile
    the package in an isolated environment, and then install it.
    =====================================================================
      $ pip install .
    =====================================================================
    If you are a software developer, and this is your own package, then
    it is usually much more efficient to install the build dependencies
    in your environment once and use the following command that avoids
    a costly creation of a new virtual environment at every compilation:
    =====================================================================
      $ pip install nanobind scikit-build-core[pyproject]
      $ pip install --no-build-isolation -ve .
    =====================================================================
    You may optionally add -Ceditable.rebuild=true to auto-rebuild when
    the package is imported. Otherwise, you need to re-run the above
    after editing C++ files.")
endif()

# Turn on to link libsoxr dynamically and not to bundle libsoxr in the wheel package
option(USE_SYSTEM_LIBSOXR "Build using system libsoxr" OFF)

find_package(Python 3.9
    REQUIRED COMPONENTS Interpreter Development.Module
    OPTIONAL_COMPONENTS Development.SABIModule)

find_package(nanobind CONFIG REQUIRED)

nanobind_add_module(soxr_ext STABLE_ABI NB_STATIC
    src/soxr_ext.cpp
)

target_link_libraries(soxr_ext PRIVATE
    soxr
)

# Install directive for scikit-build-core
install(TARGETS soxr_ext LIBRARY DESTINATION soxr)

if (NOT USE_SYSTEM_LIBSOXR)
    target_include_directories(soxr_ext PRIVATE
        libsoxr/src/
    )

    # find_package(OpenMP)
    # if (OpenMP_FOUND)
    #     target_link_libraries(soxr_ext PRIVATE OpenMP::OpenMP_CXX)
    # endif ()

    # Build static libsoxr
    option(BUILD_TESTS "" OFF)
    option(WITH_OPENMP "" OFF)
    option(WITH_LSR_BINDINGS "" OFF)
    option(BUILD_SHARED_LIBS "" OFF)  # make it shared someday?
    set(CMAKE_POSITION_INDEPENDENT_CODE ON)
    set(CMAKE_INSTALL_PREFIX ../install)
    set(CMAKE_POLICY_DEFAULT_CMP0115 OLD)  # suppress policy warnings
    add_subdirectory(libsoxr libsoxr)

    # TODO: copy license to package
endif ()
