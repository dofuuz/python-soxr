"""
Python-SoXR
https://github.com/dofuuz/python-soxr

SPDX-FileCopyrightText: (c) 2021 Myungchul Keum
SPDX-License-Identifier: LGPL-2.1-or-later

High quality, one-dimensional sample-rate conversion library for Python.
Python-SoXR is a Python wrapper of libsoxr.
"""

import numpy as np

from . import soxr_ext
from .soxr_ext import QQ, LQ, MQ, HQ, VHQ
from ._version import version as __version__


__libsoxr_version__ = soxr_ext.libsoxr_version()

# libsoxr locates memory per each channel.
# Too much channels will cause memory error.
_CH_LIMIT = 65536

_DTYPE_UNMATCH_ERR_STR = 'Input should be a `np.ndarray` with matching dtype for ResampleStream({}).'
_CH_EXEED_ERR_STR = 'Channel num({}) out of limit. Should be in [1, %d]' % _CH_LIMIT
_DTYPE_ERR_STR = 'Data type must be one of [float32, float64, int16, int32], not {}'
_QUALITY_ERR_STR = "Quality must be one of [QQ, LQ, MQ, HQ, VHQ]"


def _quality_to_enum(q):
    if q in (VHQ, HQ, MQ, LQ, QQ):
        return q

    if type(q) is int:
        raise ValueError(_QUALITY_ERR_STR)

    q = q.lower()
    if q in ('vhq', 'soxr_vhq'):
        return VHQ
    elif q in ('hq', 'soxr_hq'):
        return HQ
    elif q in ('mq', 'soxr_mq'):
        return MQ
    elif q in ('lq', 'soxr_lq'):
        return LQ
    elif q in ('qq', 'soxr_qq'):
        return QQ

    raise ValueError(_QUALITY_ERR_STR)


def _to_soxr_datatype(ntype):
    if ntype == np.float32:
        return soxr_ext.SOXR_FLOAT32_I
    elif ntype == np.float64:
        return soxr_ext.SOXR_FLOAT64_I
    elif ntype == np.int32:
        return soxr_ext.SOXR_INT32_I
    elif ntype == np.int16:
        return soxr_ext.SOXR_INT16_I
    else:
        raise TypeError(_DTYPE_ERR_STR.format(ntype))


class ResampleStream:
    """ Streaming resampler

        Use `ResampleStream` for real-time processing or very long signal.

        Parameters
        ----------
        in_rate : float
            Input sample-rate.
        out_rate : float
            Output sample-rate.
        num_channels : int
            Number of channels.
        dtype : type or str, optional
            Internal data type processed with.
            Should be one of float32, float64, int16, int32.
        quality : int or str, optional
            Quality setting.
            One of `QQ`, `LQ`, `MQ`, `HQ`, `VHQ`.
    """

    def __init__(self,
                 in_rate: float, out_rate: float, num_channels: int,
                 dtype='float32', quality='HQ'):
        if in_rate <= 0 or out_rate <= 0:
            raise ValueError('Sample rate should be over 0')

        if num_channels < 1 or _CH_LIMIT < num_channels:
            raise ValueError(_CH_EXEED_ERR_STR.format(num_channels))

        self._type = np.dtype(dtype)
        stype = _to_soxr_datatype(self._type)

        q = _quality_to_enum(quality)

        self._cysoxr = soxr_ext.CySoxr(in_rate, out_rate, num_channels, stype, q)
        self._process = getattr(self._cysoxr, f'process_{self._type}')

    def resample_chunk(self, x: np.ndarray, last=False):
        """ Resample chunk with streaming resampler

        Parameters
        ----------
        x : np.ndarray
            Input array. Input can be 1D(mono) or 2D(frames, channels).
            dtype should match with constructor.

        last : bool, optional
            Set True at end of input sequence.

        Returns
        -------
        np.ndarray
            Resampled data.
            Output is np.ndarray with same ndim with input.

        """
        if type(x) != np.ndarray or x.dtype != self._type:
            raise TypeError(_DTYPE_UNMATCH_ERR_STR.format(self._type))

        x = np.ascontiguousarray(x)    # make array C-contiguous

        if x.ndim == 1:
            y = self._process(x[:, np.newaxis], last)
            return np.squeeze(y, axis=1)
        elif x.ndim == 2:
            return self._process(x, last)
        else:
            raise ValueError('Input must be 1-D or 2-D array')


def resample(x, in_rate: float, out_rate: float, quality='HQ'):
    """ Resample signal

    Parameters
    ----------
    x : array_like
        Input array. Input can be 1D(mono) or 2D(frames, channels).
        If input is not `np.ndarray`, it will be converted to `np.ndarray(dtype='float32')`.
        Its dtype should be one of float32, float64, int16, int32.
    in_rate : float
        Input sample-rate.
    out_rate : float
        Output sample-rate.
    quality : int or str, optional
        Quality setting.
        One of `QQ`, `LQ`, `MQ`, `HQ`, `VHQ`.

    Returns
    -------
    np.ndarray
        Resampled data.
        Output is `np.ndarray` with same ndim and dtype with input.
    """
    if in_rate <= 0 or out_rate <= 0:
        raise ValueError('Sample rate should be over 0')

    if type(x) != np.ndarray:
        x = np.asarray(x, dtype=np.float32)

    try:
        divide_proc = getattr(soxr_ext, f'cysoxr_divide_proc_{x.dtype}')
    except AttributeError:
        raise TypeError(_DTYPE_ERR_STR.format(x.dtype))

    q = _quality_to_enum(quality)

    x = np.ascontiguousarray(x)    # make array C-contiguous

    if x.ndim == 1:
        y = divide_proc(in_rate, out_rate, x[:, np.newaxis], q)
        return np.squeeze(y, axis=1)
    elif x.ndim == 2:
        num_channels = x.shape[1]
        if num_channels < 1 or _CH_LIMIT < num_channels:
            raise ValueError(_CH_EXEED_ERR_STR.format(num_channels))

        return divide_proc(in_rate, out_rate, x, q)
    else:
        raise ValueError('Input must be 1-D or 2-D array')


def _resample_oneshot(x, in_rate: float, out_rate: float, quality='HQ'):
    """
    Resample using libsoxr's `soxr_oneshot()`. Use `resample()` for general use.
    `soxr_oneshot()` becomes slow with long input.
    This function exists for test purpose.
    """
    try:
        oneshot = getattr(soxr_ext, f'cysoxr_oneshot_{x.dtype}')
    except AttributeError:
        raise TypeError(_DTYPE_ERR_STR.format(x.dtype))

    if x.ndim == 1:
        y = oneshot(in_rate, out_rate, x[:, np.newaxis], _quality_to_enum(quality))
        return np.squeeze(y, axis=1)

    return oneshot(in_rate, out_rate, x, _quality_to_enum(quality))
