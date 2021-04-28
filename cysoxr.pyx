# Python wrapper for libsoxr
# https://github.com/dofuuz/python-soxr

import numpy as np

cimport cython
cimport numpy as np

cimport csoxr


cdef class Soxr:
    cdef csoxr.soxr_t _soxr

    cdef double _in_rate
    cdef double _out_rate
    cdef float [:,:] _out_buf

    def __cinit__(self, double in_rate, double out_rate, unsigned num_channels):
        self._soxr = csoxr.soxr_create(in_rate, out_rate, num_channels, NULL, NULL, NULL, NULL)
        if self._soxr is NULL:
            raise MemoryError()

        self._in_rate = in_rate
        self._out_rate = out_rate
        self._out_buf = np.zeros([0, num_channels], dtype=np.float32)

    cpdef process(self, np.ndarray[float, ndim=2, mode='c'] in_ndarray):
        cdef size_t ilen = in_ndarray.shape[0]
        cdef size_t olen = int(ilen * self._out_rate / self._in_rate + .5)
        cdef unsigned channels = in_ndarray.shape[1]

        if len(self._out_buf) < olen:
            self._out_buf = np.zeros([olen, channels], dtype=np.float32)

        cdef size_t odone
        csoxr.soxr_process(
            self._soxr,
            &(in_ndarray[0,0]), ilen, NULL,
            &(self._out_buf[0,0]), olen, &odone)

        return np.copy(self._out_buf[:odone])


cpdef object oneshot(double in_rate, double out_rate, np.ndarray[float, ndim=2, mode='c'] in_ndarray):
    cdef size_t ilen = in_ndarray.shape[0]
    cdef size_t olen = int(ilen * out_rate / in_rate + .5)
    cdef unsigned channels = in_ndarray.shape[1]

    print(olen)
    print(channels)
    cdef size_t odone
    cdef np.ndarray[float, ndim=2, mode='c'] out_ndarray = np.zeros([olen, channels], dtype=np.float32)
    csoxr.soxr_oneshot(
        in_rate, out_rate, channels, 
        &(in_ndarray[0,0]), ilen, NULL,
        &(out_ndarray[0,0]), olen, &odone,
        NULL, NULL, NULL)

    out_ndarray = out_ndarray[:odone]
    return out_ndarray

# cpdef object __version__():
#     return csoxr.soxr_version().decode('UTF-8')
