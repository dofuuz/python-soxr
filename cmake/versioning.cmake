# Generate version.c using git describe
#
# Usage:
#    set(VER_C ${CMAKE_BINARY_DIR}/ver_vcs.cpp)
#    add_custom_target(version_vcs
#        ${CMAKE_COMMAND}
#            -DVERSION_IN=${CMAKE_CURRENT_SOURCE_DIR}/ver_vcs.cpp.in
#            -DVERSION_C=${VER_C}
#            -DVCS_REPO_DIR=${CMAKE_CURRENT_SOURCE_DIR}/submodule  # optional
#            -P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/versioning.cmake
#        BYPRODUCTS ${VER_C}
#    )

if (NOT DEFINED VCS_REPO_DIR)
    set(VCS_REPO_DIR ${CMAKE_CURRENT_SOURCE_DIR})
endif ()

find_package(Git)

if (GIT_EXECUTABLE)
    execute_process(
        COMMAND ${GIT_EXECUTABLE} describe --always --tags --dirty
        OUTPUT_VARIABLE GIT_VERSION
        RESULT_VARIABLE GIT_ERROR_CODE
        OUTPUT_STRIP_TRAILING_WHITESPACE
        WORKING_DIRECTORY ${VCS_REPO_DIR}
    )
    if (NOT GIT_ERROR_CODE)
        set(VCS_VERSION ${GIT_VERSION})
    endif ()
endif ()

if (NOT DEFINED VCS_VERSION)
    set(VCS_VERSION v0.0.0-unknown)
endif ()

message("GIT_VERSION: " ${GIT_VERSION})

configure_file(${VERSION_IN} ${VERSION_C})
