# Python-SoXR
# High quality, one-dimensional sample-rate conversion library for Python
# https://github.com/dofuuz/python-soxr


import numpy as np

from .cysoxr import CySoxr
from .cysoxr import cysoxr_divide_proc_1d, cysoxr_divide_proc_2d
from .cysoxr import cysoxr_oneshot
from .cysoxr import QQ, LQ, MQ, HQ, VHQ

from .version import version as __version__


class ResampleStream():
    def __init__(self,
                 in_rate: float, out_rate: float, num_channels: int,
                 dtype=np.float32, quality=HQ):
        # internally uses NumPy sclar types, not dtype
        if type(dtype) != type:
            dtype = np.dtype(dtype).type
        if not dtype in (np.float32, np.float64, np.int16, np.int32):
            raise ValueError("Data type must be one of ['float32', 'float64', 'int16', 'int32'] and not {}".format(dtype))

        self._type = dtype

        self._cysoxr = CySoxr(in_rate, out_rate, num_channels, self._type, quality)

    def resample_chunk(self, x, last=False):
        if type(x) != np.ndarray or x.dtype.type != self._type:
            x = np.asarray(x, dtype=self._type)

        return self._cysoxr.process(x, last)


def resample(x, in_rate: float, out_rate: float, quality=HQ):
    if type(x) != np.ndarray:
        x = np.asarray(x, dtype=np.float32)

    if not x.dtype.type in (np.float32, np.float64, np.int16, np.int32):
        raise ValueError("Data type must be one of ['float32', 'float64', 'int16', 'int32'] and not {}".format(x.dtype.type))

    x = np.ascontiguousarray(x)    # make array C-contiguous

    if x.ndim == 1:
        return cysoxr_divide_proc_1d(in_rate, out_rate, x, quality)
    elif x.ndim == 2:
        return cysoxr_divide_proc_2d(in_rate, out_rate, x, quality)
    else:
        raise ValueError('Input must be 1-D or 2-D array')


def _resample_oneshot(x, in_rate: float, out_rate: float, quality=HQ):
    if type(x) != np.ndarray:
        x = np.asarray(x, dtype=np.float32)

    if not x.dtype.type in (np.float32, np.float64, np.int16, np.int32):
        raise ValueError("Data type must be one of ['float32', 'float64', 'int16', 'int32'] and not {}".format(x.dtype.type))

    return cysoxr_oneshot(in_rate, out_rate, x, quality)
