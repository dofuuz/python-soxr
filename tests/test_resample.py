"""
Python-SoXR
https://github.com/dofuuz/python-soxr

SPDX-FileCopyrightText: (c) 2021 Myungchul Keum
SPDX-License-Identifier: LGPL-2.1-or-later

High quality, one-dimensional sample-rate conversion library for Python.
Python-SoXR is a Python wrapper of libsoxr.
"""

import numpy as np
import pytest
import soxr


@pytest.mark.xfail(raises=ValueError, strict=True)
@pytest.mark.parametrize('in_rate, out_rate', [(100, 0), (100, -1), (0, 100), (-1, 100)])
def test_bad_sr(in_rate, out_rate):
    x = np.zeros(100)
    soxr.resample(x, in_rate, out_rate)


@pytest.mark.parametrize('dtype', [np.float32, np.float64, np.int16, np.int32])
def test_dtype(dtype):
    x = np.random.randn(100).astype(dtype)

    y = soxr.resample(x, 100, 200)

    assert x.dtype == y.dtype


@pytest.mark.xfail(raises=(TypeError, ValueError), strict=True)
@pytest.mark.parametrize('dtype', [np.complex64, np.complex128, np.int8, np.int64])
def test_bad_dtype(dtype):
    x = np.zeros(100, dtype=dtype)
    soxr.resample(x, 100, 200)


@pytest.mark.parametrize('in_rate, out_rate', [(44100, 32000), (32000, 44100)])
@pytest.mark.parametrize('dtype', [np.float32, np.float64])
def test_divide_match(in_rate, out_rate, dtype):
    x = np.random.randn(49999).astype(dtype)

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)
    y_divide = soxr.resample(x, in_rate, out_rate)

    assert np.allclose(y_oneshot, y_divide)


@pytest.mark.parametrize('in_rate, out_rate', [(44100, 32000), (32000, 44100)])
@pytest.mark.parametrize('length', [0, 1, 2, 99, 100, 101, 31999, 32000, 32001, 34828, 34829, 34830, 44099, 44100, 44101, 47999, 48000, 48001, 66149, 66150, 266151])
def test_length_match(in_rate, out_rate, length):
    x = np.random.randn(length).astype(np.float32)

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)
    y_divide = soxr.resample(x, in_rate, out_rate)

    assert np.allclose(y_oneshot, y_divide)


@pytest.mark.parametrize('channels', [1, 2, 3, 5, 7, 97, 197])
def test_channel_match(channels):
    x = np.random.randn(30011, channels).astype(np.float32)

    y_oneshot = soxr._resample_oneshot(x, 44100, 32000)
    y_divide = soxr.resample(x, 44100, 32000)

    assert np.allclose(y_oneshot, y_divide)


@pytest.mark.parametrize('in_rate, out_rate', [(44100, 32000), (32000, 44100)])
@pytest.mark.parametrize('dtype', [np.float32, np.float64])
@pytest.mark.parametrize('channels', [1, 2])
def test_stream_match(in_rate, out_rate, dtype, channels):
    CHUNK_SIZE = 509
    x = np.random.randn(49999, channels).astype(dtype)

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)

    rs_stream = soxr.ResampleStream(in_rate, out_rate, channels, dtype=dtype)

    y_list = []
    for idx in range(0, len(x), CHUNK_SIZE):
        end = idx + CHUNK_SIZE
        eof = False
        if len(x) <= end:
            eof = True
            end = len(x)
        y_chunk = rs_stream.resample_chunk(x[idx:end], last=eof)
        y_list.append(y_chunk)

    y_stream = np.concatenate(y_list)

    assert np.allclose(y_oneshot, y_stream)


@pytest.mark.parametrize('in_rate, out_rate', [(44100, 32000), (32000, 44100)])
@pytest.mark.parametrize('chunk_size', [7, 50, 101, 44100])
@pytest.mark.parametrize('length', [0, 1, 100, 101, 31999, 32000, 44100, 44101, 266151])
def test_stream_length(in_rate, out_rate, chunk_size, length):
    x = np.random.randn(length, 1).astype(np.float32)

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)

    rs_stream = soxr.ResampleStream(in_rate, out_rate, 1, dtype=np.float32)

    y_list = [np.ndarray([0, 1], dtype=np.float32)]
    for idx in range(0, len(x), chunk_size):
        end = idx + chunk_size
        eof = False
        if len(x) <= end:
            eof = True
            end = len(x)
        y_chunk = rs_stream.resample_chunk(x[idx:end], last=eof)
        y_list.append(y_chunk)

    y_stream = np.concatenate(y_list)

    assert np.allclose(y_oneshot, y_stream)


def make_tone(freq, sr, duration):
    return np.sin(2 * np.pi * freq / sr * np.arange(int(sr * duration)))


@pytest.mark.parametrize('in_rate,out_rate', [(44100, 22050), (22050, 32000)])
@pytest.mark.parametrize('quality', ['VHQ', 'HQ', 'MQ', 'LQ', 'QQ'])
def test_quality_sine(in_rate, out_rate, quality):
    FREQ = 32.0
    DURATION = 2.0
    IG = 50  # ignore popping at start/end

    x = make_tone(FREQ, in_rate, DURATION)
    y = make_tone(FREQ, out_rate, DURATION)

    y_pred = soxr.resample(x, in_rate, out_rate, quality=quality)

    assert np.allclose(y[IG:-IG], y_pred[IG:-IG], atol=1e-4)


@pytest.mark.parametrize('in_rate,out_rate', [(48000, 24000), (32000, 44100)])
@pytest.mark.parametrize('dtype', [np.int32, np.int16])
def test_int_sine(in_rate, out_rate, dtype):
    FREQ = 32.0
    DURATION = 2.0
    IG = 50  # ignore popping at start/end

    x = (make_tone(FREQ, in_rate, DURATION) * 16384).astype(dtype)
    y = (make_tone(FREQ, out_rate, DURATION) * 16384).astype(dtype)

    y_pred = soxr.resample(x, in_rate, out_rate)

    assert np.allclose(y[IG:-IG], y_pred[IG:-IG], atol=2)
