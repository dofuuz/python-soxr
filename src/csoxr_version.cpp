// versioning for USE_SYSTEM_LIBSOXR

#include <soxr.h>
#include "csoxr_version.h"

const char * libsoxr_version() {
    return soxr_version();
}
