# distutils: language=C

# Cython wrapper for libsoxr
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
    # Default runtime_spec is per soxr_runtime_spec(1)

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

    # Common stream resampler operations:
    cdef soxr_error_t soxr_error(soxr_t)   # Query error status.
    cdef size_t   * soxr_num_clips(soxr_t) # Query int. clip counter (for R/W).
    cdef double     soxr_delay(soxr_t)  # Query current delay in output samples.
    cdef const char * soxr_engine(soxr_t)  # Query resampling engine name.

    cdef soxr_error_t soxr_clear(soxr_t) # Ready for fresh signal, same config.
    cdef void         soxr_delete(soxr_t)  # Free resources.

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

    # -------------------------- API type definitions --------------------------

    ctypedef enum soxr_datatype_t:  # Datatypes supported for I/O to/from the resampler:
        # Internal; do not use:
        SOXR_FLOAT32, SOXR_FLOAT64, SOXR_INT32, SOXR_INT16, SOXR_SPLIT = 4,

        # Use for interleaved channels:
        SOXR_FLOAT32_I = SOXR_FLOAT32, SOXR_FLOAT64_I, SOXR_INT32_I, SOXR_INT16_I,

        # Use for split channels:
        SOXR_FLOAT32_S = SOXR_SPLIT  , SOXR_FLOAT64_S, SOXR_INT32_S, SOXR_INT16_S

    # -------------------------- API type constructors -------------------------

    cdef soxr_quality_spec_t soxr_quality_spec(
        unsigned long recipe,       # Per the #defines immediately below.
        unsigned long flags)        # As soxr_quality_spec_t.flags.

    cdef enum soxr_quality_recipe_t:
        SOXR_QQ
        SOXR_LQ
        SOXR_MQ
        SOXR_HQ
        SOXR_VHQ

    cdef soxr_io_spec_t soxr_io_spec(
        soxr_datatype_t itype,
        soxr_datatype_t otype)
