# Python-SoXR
# https://github.com/dofuuz/python-soxr

# SPDX-FileCopyrightText: (c) 2021 Myungchul Keum
# SPDX-License-Identifier: LGPL-2.1-or-later

# High quality, one-dimensional sample-rate conversion library for Python.
# Python-SoXR is a Python wrapper of libsoxr.

import numpy as np
from numpy.typing import ArrayLike

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

_QUALITY_ENUM_DICT = {
    VHQ: VHQ, 'vhq': VHQ, 'soxr_vhq': VHQ,
    HQ: HQ, 'hq': HQ, 'soxr_hq': HQ,
    MQ: MQ, 'mq': MQ, 'soxr_mq': MQ,
    LQ: LQ, 'lq': LQ, 'soxr_lq': LQ,
    QQ: QQ, 'qq': QQ, 'soxr_qq': QQ,
}


def _quality_to_enum(q):
    if isinstance(q, str):
        q = q.lower()

    try:
        return _QUALITY_ENUM_DICT[q]
    except (KeyError, TypeError):
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

        self._csoxr = soxr_ext.CSoxr(in_rate, out_rate, num_channels, stype, q)
        self._process = getattr(self._csoxr, f'process_{self._type}')

    def resample_chunk(self, x: np.ndarray, last=False) -> np.ndarray:
        """ Resample chunk with streaming resampler

        Parameters
        ----------
        x : np.ndarray
            Input array. Input can be mono(1D) or multi-channel(2D of [frame, channel]).
            dtype should match with constructor.

        last : bool, optional
            Set True at final chunk to flush last outputs.
            It should be `True` only once at the end of a continuous sequence.

        Returns
        -------
        np.ndarray
            Resampled data.
            Output is np.ndarray with same ndim with input.

        """
        if type(x) != np.ndarray or x.dtype != self._type:
            raise TypeError(_DTYPE_UNMATCH_ERR_STR.format(self._type))

        if x.ndim == 1:
            y = self._process(x[:, np.newaxis], last)
            return np.squeeze(y, axis=1)
        elif x.ndim == 2:
            return self._process(x, last)
        else:
            raise ValueError('Input must be 1-D or 2-D array')

    def num_clips(self) -> int:
        """ Clip counter. (for int I/O)

        Returns
        -------
        int
            Count of clipped samples.
        """
        return self._csoxr.num_clips()

    def delay(self) -> float:
        """ Get current delay.

        SoXR output has an algorithmic delay. This function returns the length of current pending output.

        Returns
        -------
        float
            Current delay in output samples.
        """
        return self._csoxr.delay()

    def clear(self) -> None:
        """ Reset resampler. Ready for fresh signal, same config.

        This can be used to save initialization time.
        """
        self._csoxr.clear()


def resample(x: ArrayLike, in_rate: float, out_rate: float, quality='HQ') -> np.ndarray:
    """ Resample signal

    Parameters
    ----------
    x : array_like
        Input array. Input can be mono(1D) or multi-channel(2D of [frame, channel]).
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
        if x.strides[0] == x.itemsize:  # split channel memory layout
            divide_proc = getattr(soxr_ext, f'csoxr_split_ch_{x.dtype}')
        else:
            divide_proc = getattr(soxr_ext, f'csoxr_divide_proc_{x.dtype}')
    except AttributeError:
        raise TypeError(_DTYPE_ERR_STR.format(x.dtype))

    q = _quality_to_enum(quality)

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


def _resample_oneshot(x: np.ndarray, in_rate: float, out_rate: float, quality='HQ') -> np.ndarray:
    """
    Resample using libsoxr's `soxr_oneshot()`. Use `resample()` for general use.
    `soxr_oneshot()` becomes slow with long input.
    This function exists for test purpose.
    """
    try:
        oneshot = getattr(soxr_ext, f'csoxr_oneshot_{x.dtype}')
    except AttributeError:
        raise TypeError(_DTYPE_ERR_STR.format(x.dtype))

    if x.ndim == 1:
        y = oneshot(in_rate, out_rate, x[:, np.newaxis], _quality_to_enum(quality))
        return np.squeeze(y, axis=1)

    return oneshot(in_rate, out_rate, x, _quality_to_enum(quality))
