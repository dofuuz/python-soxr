# Python wrapper for libsoxr
# https://github.com/dofuuz/python-soxr

cimport cython

import numpy as np
cimport numpy as np

cimport csoxr


ctypedef fused datatype_t:
    cython.float
    cython.double
    cython.int
    cython.short
    

# NumPy scalar type to soxr_io_spec_t
cdef csoxr.soxr_io_spec_t to_io_spec(type dtype):
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
        raise ValueError('Data type not support')
    
    return csoxr.soxr_io_spec(io_type, io_type)


cdef class CySoxr:
    cdef csoxr.soxr_t _soxr
    cdef double _in_rate
    cdef double _out_rate
    cdef type _dtype

    def __cinit__(self, double in_rate, double out_rate, unsigned num_channels, type dtype):
        self._in_rate = in_rate
        self._out_rate = out_rate
        self._dtype = dtype

        cdef csoxr.soxr_io_spec_t io_spec = to_io_spec(dtype)

        self._soxr = csoxr.soxr_create(in_rate, out_rate, num_channels, NULL, &io_spec, NULL, NULL)
        if self._soxr is NULL:
            raise MemoryError()

    def __dealloc__(self):
        csoxr.soxr_delete(self._soxr)

    cpdef datatype_t[:, ::1] process(self, datatype_t[:, ::1] x, bint eof=False):
        cdef size_t ilen = x.shape[0]
        cdef size_t olen = np.ceil(ilen * self._out_rate / self._in_rate)
        cdef unsigned channels = x.shape[1]

        # Cython type to NumPy scalar type
        cdef type dtype
        if datatype_t is cython.float:
            dtype = np.float32
        elif datatype_t is cython.double:
            dtype = np.float64
        elif datatype_t is cython.int:
            dtype = np.int32
        elif datatype_t is cython.short:
            dtype = np.int16

        if dtype != self._dtype:
            raise ValueError('Data type not match')

        # x = np.ascontiguousarray(x)
        cdef datatype_t[:, ::1] out_buf = np.zeros([olen, channels], dtype=dtype, order='c')
        cdef size_t odone

        csoxr.soxr_process(
            self._soxr,
            &x[0,0], ilen, NULL,
            &out_buf[0,0], olen, &odone)

        out_buf = out_buf[:odone]

        cdef datatype_t[:, ::1] eof_buf
        cdef int delay
        if (eof):
            delay = int(csoxr.soxr_delay(self._soxr) + .5)
            eof_buf = np.zeros([delay, channels], dtype=dtype, order='c')
            csoxr.soxr_process(
                self._soxr,
                NULL, 0, NULL,
                &eof_buf[0,0], delay, &odone)

            eof_buf = eof_buf[:odone]

            out_buf = np.vstack([out_buf, eof_buf])

        return out_buf
    
    @cython.boundscheck(False)  # Deactivate bounds checking
    @cython.wraparound(False)   # Deactivate negative indexing.
    cpdef datatype_t[::1] process_1d(self, datatype_t[::1] x, bint eof=False):
        cdef size_t ilen = x.shape[0]
        cdef size_t olen = np.ceil(ilen * self._out_rate / self._in_rate)

        # Cython type to NumPy scalar type
        cdef type dtype
        if datatype_t is cython.float:
            dtype = np.float32
        elif datatype_t is cython.double:
            dtype = np.float64
        elif datatype_t is cython.int:
            dtype = np.int32
        elif datatype_t is cython.short:
            dtype = np.int16

        if dtype != self._dtype:
            raise ValueError('Data type not match')

        # x = np.ascontiguousarray(x)
        cdef datatype_t[::1] out_buf = np.zeros([olen], dtype=dtype, order='c')
        cdef size_t odone

        csoxr.soxr_process(
            self._soxr,
            &x[0], ilen, NULL,
            &out_buf[0], olen, &odone)

        out_buf = out_buf[:odone]

        cdef datatype_t[::1] eof_buf
        cdef int delay
        if (eof):
            delay = int(csoxr.soxr_delay(self._soxr) + .5)
            eof_buf = np.zeros([delay], dtype=dtype, order='c')
            csoxr.soxr_process(
                self._soxr,
                NULL, 0, NULL,
                &eof_buf[0], delay, &odone)

            eof_buf = eof_buf[:odone]

            out_buf = np.hstack([out_buf, eof_buf])

        return out_buf


cpdef datatype_t[:, ::1] cysoxr_oneshot(double in_rate, double out_rate, datatype_t[:, ::1] x):
    cdef size_t ilen = x.shape[0]
    cdef size_t olen = np.ceil(ilen * out_rate / in_rate)
    cdef unsigned channels = x.shape[1]

    # Cython type to NumPy scalar type
    cdef type dtype
    if datatype_t is cython.float:
        dtype = np.float32
    elif datatype_t is cython.double:
        dtype = np.float64
    elif datatype_t is cython.int:
        dtype = np.int32
    elif datatype_t is cython.short:
        dtype = np.int16

    # make soxr config
    cdef csoxr.soxr_io_spec_t io_spec = to_io_spec(dtype)
    cdef csoxr.soxr_quality_spec_t quality = csoxr.soxr_quality_spec(csoxr.SOXR_HQ, 0)

    # x = np.ascontiguousarray(x)    # make array C-contiguous

    cdef size_t odone
    cdef datatype_t[:, ::1] y = np.zeros([olen, channels], dtype=dtype, order='c')

    csoxr.soxr_oneshot(
        in_rate, out_rate, channels,
        &x[0,0], ilen, NULL,
        &y[0,0], olen, &odone,
        &io_spec, &quality, NULL)

    return y[:odone]
