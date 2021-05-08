# Python wrapper for libsoxr
# https://github.com/dofuuz/python-soxr


from .cysoxr import CySoxr, cysoxr_oneshot
import numpy as np


class ResampleStream():
    def __init__(self, in_rate: float, out_rate: float, num_channels: int, dtype=np.float32):
        # internally uses Sclar types, not dtype
        if type(dtype) != type:
            dtype = np.dtype(dtype).type
        if not dtype in (np.float32, np.float64, np.int16, np.int32):
            raise ValueError("dtype must be one of ['float32', 'float64', 'int16', 'int32'] and not {}".format(dtype))

        self._type = dtype

        self._cysoxr = CySoxr(in_rate, out_rate, num_channels, self._type)

    def resample_chunk(self, x, end=False):
        if type(x) != np.ndarray or x.dtype.type != self._type:
            x = np.asarray(x, dtype=self._type)

        return self._cysoxr.process(x, end)


def resample(x, in_rate: float, out_rate: float):
    if type(x) != np.ndarray:
        x = np.asarray(x, dtype=np.float32)

    if not x.dtype.type in (np.float32, np.float64, np.int16, np.int32):
        raise ValueError("dtype must be one of ['float32', 'float64', 'int16', 'int32'] and not {}".format(x.dtype.type))

    return cysoxr_oneshot(in_rate, out_rate, x)
