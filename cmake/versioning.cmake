# Generate version.c using git describe
#
# Usage:
#    set(VER_C ${CMAKE_BINARY_DIR}/ver_vcs.cpp)
#    add_custom_target(version_vcs
#        ${CMAKE_COMMAND}
#            -DVERSION_IN=ver_vcs.cpp.in
#            -DVERSION_C=${VER_C}
#            -DVCS_REPO_DIR=submodule  # optional
#            -P cmake/versioning.cmake
#        BYPRODUCTS ${VER_C}
#        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
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

get_filename_component(VCS_MODULE ${VCS_REPO_DIR} NAME)
if (VCS_VERSION)
    message("${VCS_MODULE} VCS_VERSION: " ${VCS_VERSION})
    configure_file(${VERSION_IN} ${VERSION_C})
else ()
    message("${VCS_MODULE} VCS_VERSION unknown. ${VERSION_C} not changed.")
endif ()
