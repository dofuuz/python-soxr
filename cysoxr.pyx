# Python wrapper for libsoxr
# https://github.com/dofuuz/python-soxr

import numpy as np
cimport numpy as np

cimport csoxr


# NumPy scalar type to soxr_io_spec_t
cdef csoxr.soxr_io_spec_t to_io_spec(type ntype):
    cdef csoxr.soxr_datatype_t io_type
    if ntype == np.float32:
        io_type = csoxr.SOXR_FLOAT32_I
    elif ntype == np.float64:
        io_type = csoxr.SOXR_FLOAT64_I
    elif ntype == np.int32:
        io_type = csoxr.SOXR_INT32_I
    elif ntype == np.int16:
        io_type = csoxr.SOXR_INT16_I
    else:
        raise ValueError('Data type not support')

    return csoxr.soxr_io_spec(io_type, io_type)


cdef class CySoxr:
    cdef csoxr.soxr_t _soxr
    cdef double _in_rate
    cdef double _out_rate
    cdef type _ntype

    def __cinit__(self, double in_rate, double out_rate, unsigned num_channels, type ntype):
        self._in_rate = in_rate
        self._out_rate = out_rate
        self._ntype = ntype

        cdef csoxr.soxr_io_spec_t io_spec = to_io_spec(ntype)

        self._soxr = csoxr.soxr_create(in_rate, out_rate, num_channels, NULL, &io_spec, NULL, NULL)
        if self._soxr is NULL:
            raise MemoryError()

    def __dealloc__(self):
        csoxr.soxr_delete(self._soxr)

    cpdef np.ndarray process(self, np.ndarray x, bint last=False):
        if 2 < x.ndim:
            raise ValueError('Input must be 1-D or 2-D array')

        cdef size_t ilen = x.shape[0]
        cdef size_t olen = np.ceil(ilen * self._out_rate / self._in_rate)
        cdef unsigned channels = 1
        if 2 == x.ndim:
            channels = x.shape[1]

        cdef type ntype = x.dtype.type
        if ntype != self._ntype:
            raise ValueError('Data type not match')

        x = np.ascontiguousarray(x)
        cdef np.ndarray y
        if 1 == x.ndim:
            y = np.zeros([olen], dtype=ntype, order='c')
        else:
            y = np.zeros([olen, channels], dtype=ntype, order='c')

        cdef size_t odone
        csoxr.soxr_process(
            self._soxr,
            x.data, ilen, NULL,
            y.data, olen, &odone)

        y = y[:odone]

        # flush if last input
        cdef np.ndarray last_buf
        cdef int delay
        if last:
            delay = int(csoxr.soxr_delay(self._soxr) + .5)

            if 1 == x.ndim:
                last_buf = np.zeros([delay], dtype=ntype, order='c')
            else:
                last_buf = np.zeros([delay, channels], dtype=ntype, order='c')

            csoxr.soxr_process(
                self._soxr,
                NULL, 0, NULL,
                last_buf.data, delay, &odone)

            last_buf = last_buf[:odone]

            y = np.concatenate([y, last_buf])

        return y


cpdef np.ndarray cysoxr_oneshot(double in_rate, double out_rate, np.ndarray x):
    if 2 < x.ndim:
        raise ValueError('Input must be 1-D or 2-D array')

    cdef size_t ilen = x.shape[0]
    cdef size_t olen = np.ceil(ilen * out_rate / in_rate)
    cdef unsigned channels = 1
    if 2 == x.ndim:
        channels = x.shape[1]

    cdef type ntype = x.dtype.type

    # make soxr config
    cdef csoxr.soxr_io_spec_t io_spec = to_io_spec(ntype)
    cdef csoxr.soxr_quality_spec_t quality = csoxr.soxr_quality_spec(csoxr.SOXR_HQ, 0)

    x = np.ascontiguousarray(x)    # make array C-contiguous

    cdef size_t odone
    cdef np.ndarray y 
    if 1 == x.ndim:
        y = np.zeros([olen], dtype=ntype, order='c')
    else:
        y = np.zeros([olen, channels], dtype=ntype, order='c')

    csoxr.soxr_oneshot(
        in_rate, out_rate, channels,
        x.data, ilen, NULL,
        y.data, olen, &odone,
        &io_spec, &quality, NULL)

    return y[:odone]
