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

if (USE_SYSTEM_LIBSOXR)
    set(CSOXR_VER_C src/csoxr_version.cpp)
else ()
    # libsoxr VCS versioning
    set(CSOXR_VER_C ${CMAKE_CURRENT_SOURCE_DIR}/src/csoxr_ver_vcs.cpp)
    set(SOXR_VER_COMMAND ${CMAKE_COMMAND}
            -DVERSION_IN=src/csoxr_ver_vcs.cpp.in
            -DVERSION_C=${CSOXR_VER_C}
            -DVCS_REPO_DIR=libsoxr
            -P cmake/versioning.cmake
    )

    # run while CMake configuring (for sdist)
    execute_process(
        COMMAND ${SOXR_VER_COMMAND}
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    # run at every build time
    add_custom_target(soxr_version_vcs
        COMMAND ${SOXR_VER_COMMAND}
        BYPRODUCTS ${CSOXR_VER_C}
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
endif ()

nanobind_add_module(soxr_ext STABLE_ABI FREE_THREADED NB_STATIC
    src/soxr_ext.cpp
    ${CSOXR_VER_C}
)

if (NOT CMAKE_CROSSCOMPILING)
    # nanobind's stub generation requires importing the module, so skip it when cross-compiling
    nanobind_add_stub(soxr_ext_stub
        MODULE soxr_ext
        OUTPUT soxr_ext.pyi
        PYTHON_PATH $<TARGET_FILE_DIR:soxr_ext>
        DEPENDS soxr_ext
    )

    install(FILES ${CMAKE_BINARY_DIR}/soxr_ext.pyi DESTINATION soxr)
endif ()

# Install directive for scikit-build-core
install(TARGETS soxr_ext LIBRARY DESTINATION soxr)

if (USE_SYSTEM_LIBSOXR)
    # Find system libsoxr
    find_library(SOXR_LIBRARY NAMES soxr)
    find_path(SOXR_INCLUDE_DIR soxr.h)

    message (STATUS "Building with external libsoxr")
    message(SOXR_LIBRARY="${SOXR_LIBRARY}")
    message(SOXR_INCLUDE_DIR="${SOXR_INCLUDE_DIR}")

    target_link_libraries(soxr_ext PRIVATE ${SOXR_LIBRARY})
    target_include_directories(soxr_ext PRIVATE ${SOXR_INCLUDE_DIR})

else ()
    target_link_libraries(soxr_ext PRIVATE soxr)
    target_include_directories(soxr_ext PRIVATE
        src
        libsoxr/src
    )

    # Build static libsoxr
    option(BUILD_TESTS "" OFF)
    option(WITH_OPENMP "" OFF)  # OpenMP seems not working (dunno why). Disable it for portability anyway.
    option(WITH_LSR_BINDINGS "" OFF)
    option(BUILD_SHARED_LIBS "" OFF)  # make it shared someday?
    option(WITH_VR32 "" OFF)
    set(CMAKE_POSITION_INDEPENDENT_CODE ON)
    set(CMAKE_INSTALL_PREFIX ../install)
    add_subdirectory(libsoxr libsoxr)

    # Copy licenses to package (scikit-build-core)
    install(FILES cmake/LICENSE-PFFFT.txt DESTINATION ${SKBUILD_METADATA_DIR}/licenses)
    install(FILES libsoxr/LICENCE DESTINATION ${SKBUILD_METADATA_DIR}/licenses RENAME LICENSE-libsoxr.txt)
endif ()
