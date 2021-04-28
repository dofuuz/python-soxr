# distutils: language=C

# Python wrapper for libsoxr
# https://github.com/dofuuz/python-soxr

cdef extern from 'soxr.h':
    ctypedef struct soxr_io_spec_t:
        pass
    ctypedef struct soxr_quality_spec_t:
        pass
    ctypedef struct soxr_runtime_spec_t:
        pass

    # --------------------------- Type declarations ----------------------------

    ctypedef struct soxr:
        pass
    ctypedef soxr * soxr_t
    ctypedef const char * soxr_error_t                 # 0:no-error; non-0:error.

    ctypedef const void * soxr_in_t
    ctypedef void       * soxr_out_t

    # --------------------------- API main functions ---------------------------

    cdef const char * soxr_version()   # Query library version: "libsoxr-x.y.z"

    # Create a stream resampler:
    cdef soxr_t soxr_create(
        double      input_rate,      # Input sample-rate.
        double      output_rate,     # Output sample-rate.
        unsigned    num_channels,    # Number of channels to be used.
            # All following arguments are optional (may be set to NULL).
        soxr_error_t *,              # To report any error during creation.
        const soxr_io_spec_t *,      # To specify non-default I/O formats.
        const soxr_quality_spec_t *, # To specify non-default resampling quality.
        const soxr_runtime_spec_t *) # To specify non-default runtime resources.
    # Default io_spec      is per soxr_io_spec(SOXR_FLOAT32_I, SOXR_FLOAT32_I)
    # Default quality_spec is per soxr_quality_spec(SOXR_HQ, 0)
    # Default runtime_spec is per soxr_runtime_spec(1)                          */

    # If not using an app-supplied input function, after creating a stream
    # resampler, repeatedly call:
    cdef soxr_error_t soxr_process(
        soxr_t      resampler,      # As returned by soxr_create.
                                # Input (to be resampled):
        soxr_in_t   in_,            # Input buffer(s); may be NULL (see below).
        size_t      ilen,           # Input buf. length (samples per channel).
        size_t      * idone,        # To return actual # samples used (<= ilen).
                                # Output (resampled):
        soxr_out_t  out,            # Output buffer(s).
        size_t      olen,           # Output buf. length (samples per channel).
        size_t      * odone)        # To return actual # samples out (<= olen).
    # Note that no special meaning is associated with ilen or olen equal to
    # zero.  End-of-input (i.e. no data is available nor shall be available)
    # may be indicated by seting `in' to NULL.

    # `Short-cut', single call to resample a (probably short) signal held entirely
    # in memory.  See soxr_create and soxr_process above for parameter details.
    # Note that unlike soxr_create however, the default quality spec. for
    # soxr_oneshot is per soxr_quality_spec(SOXR_LQ, 0).
    cdef soxr_error_t soxr_oneshot(
        double         input_rate,
        double         output_rate,
        unsigned       num_channels,
        soxr_in_t    in_, size_t ilen, size_t * idone,
        soxr_out_t   out, size_t olen, size_t * odone,
        const soxr_io_spec_t *,
        const soxr_quality_spec_t *,
        const soxr_runtime_spec_t *)

    cdef enum soxr_datatype_t:          # Datatypes supported for I/O to/from the resampler: */
        # Internal; do not use:
        SOXR_FLOAT32, SOXR_FLOAT64, SOXR_INT32, SOXR_INT16, SOXR_SPLIT = 4,

        # Use for interleaved channels:
        SOXR_FLOAT32_I = SOXR_FLOAT32, SOXR_FLOAT64_I, SOXR_INT32_I, SOXR_INT16_I,

        # Use for split channels:
        SOXR_FLOAT32_S = SOXR_SPLIT  , SOXR_FLOAT64_S, SOXR_INT32_S, SOXR_INT16_S

    ctypedef struct soxr_io_spec:                                     # Typically
        soxr_datatype_t itype     # Input datatype.                SOXR_FLOAT32_I
        soxr_datatype_t otype     # Output datatype.               SOXR_FLOAT32_I
        double scale              # Linear gain to apply during resampling.  1
        void * e                  # Reserved for internal use                0
        unsigned long flags       # Per the following #defines.              0
