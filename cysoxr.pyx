# Python wrapper for libsoxr
# https://github.com/dofuuz/python-soxr

import numpy as np
cimport numpy as np

cimport csoxr


cdef class CySoxr:
    cdef csoxr.soxr_t _soxr
    cdef double _in_rate
    cdef double _out_rate
    cdef type _dtype

    def __cinit__(self, double in_rate, double out_rate, unsigned num_channels, type dtype):
        self._in_rate = in_rate
        self._out_rate = out_rate
        self._dtype = dtype

        cdef csoxr.soxr_datatype_t io_type
        if dtype == np.float32:
            io_type = csoxr.SOXR_FLOAT32_I
        elif dtype == np.float64:
            io_type = csoxr.SOXR_FLOAT64_I
        elif dtype == np.int32:
            io_type = csoxr.SOXR_INT32_I
        elif dtype == np.int16:
            io_type = csoxr.SOXR_INT16_I
        else:
            raise ValueError('Dtype not support')

        cdef csoxr.soxr_io_spec_t io_spec = csoxr.soxr_io_spec(io_type, io_type)

        self._soxr = csoxr.soxr_create(in_rate, out_rate, num_channels, NULL, &io_spec, NULL, NULL)
        if self._soxr is NULL:
            raise MemoryError()

    def __dealloc__(self):
        csoxr.soxr_delete(self._soxr)

    cpdef np.ndarray process(self, np.ndarray x, bint eof=False):
        if 2 < x.ndim:
            raise ValueError('Input must be 1-D or 2-D array')

        cdef size_t ilen = x.shape[0]
        cdef size_t olen = np.ceil(ilen * self._out_rate / self._in_rate)
        cdef unsigned channels = 1
        if 2 == x.ndim:
            channels = x.shape[1]

        dtype = x.dtype
        if dtype != self._dtype:
            raise ValueError('Dtype not match')

        x = np.ascontiguousarray(x)
        cdef np.ndarray out_buf = np.zeros([olen, channels], dtype=dtype, order='c')
        cdef size_t odone

        csoxr.soxr_process(
            self._soxr,
            x.data, ilen, NULL,
            out_buf.data, olen, &odone)

        out_buf = out_buf[:odone]

        cdef np.ndarray eof_buf
        cdef int delay
        if (eof):
            delay = int(csoxr.soxr_delay(self._soxr) + .5)
            eof_buf = np.zeros([delay, channels], dtype=dtype, order='c')
            csoxr.soxr_process(
                self._soxr,
                NULL, 0, NULL,
                eof_buf.data, delay, &odone)

            eof_buf = eof_buf[:odone]

            out_buf = np.vstack([out_buf, eof_buf])

        return out_buf

        # return np.copy(self._out_buf[:odone])


cpdef np.ndarray cysoxr_oneshot(double in_rate, double out_rate, np.ndarray x):
    if 2 < x.ndim:
        raise ValueError('Input must be 1-D or 2-D array')

    cdef size_t ilen = x.shape[0]
    cdef size_t olen = np.ceil(ilen * out_rate / in_rate)
    cdef unsigned channels = 1
    if 2 == x.ndim:
        channels = x.shape[1]

    dtype = x.dtype

    cdef csoxr.soxr_datatype_t io_type
    if dtype == np.float32:
        io_type = csoxr.SOXR_FLOAT32_I
    elif dtype == np.float64:
        io_type = csoxr.SOXR_FLOAT64_I
    elif dtype == np.int32:
        io_type = csoxr.SOXR_INT32_I
    elif dtype == np.int16:
        io_type = csoxr.SOXR_INT16_I
    else:
        raise ValueError('Dtype not support')

    cdef csoxr.soxr_io_spec_t io_spec = csoxr.soxr_io_spec(io_type, io_type)
    cdef csoxr.soxr_quality_spec_t quality = csoxr.soxr_quality_spec(csoxr.SOXR_HQ, 0)

    x = np.ascontiguousarray(x)    # make array C-contiguous

    cdef size_t odone
    cdef np.ndarray out_ndarray = np.zeros([olen, channels], dtype=dtype, order='c')

    csoxr.soxr_oneshot(
        in_rate, out_rate, channels,
        x.data, ilen, NULL,
        out_ndarray.data, olen, &odone,
        &io_spec, &quality, NULL)

    return out_ndarray[:odone]
