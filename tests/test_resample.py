"""
Python-SoXR
https://github.com/dofuuz/python-soxr

SPDX-FileCopyrightText: (c) 2021 Myungchul Keum
SPDX-License-Identifier: LGPL-2.1-or-later

High quality, one-dimensional sample-rate conversion library for Python.
Python-SoXR is a Python wrapper of libsoxr.
"""

from concurrent.futures import ThreadPoolExecutor
from functools import partial

import numpy as np
import pytest
import soxr


@pytest.mark.parametrize('in_rate, out_rate', [(100, 0), (50, -1), (0, 100.5), (-1.5, 100)])
def test_bad_sr(in_rate, out_rate):
    # test invalid samplerate
    x = np.zeros(100)
    with pytest.raises(ValueError):
        soxr.resample(x, in_rate, out_rate)


@pytest.mark.parametrize('dtype', [np.float32, np.float64, np.int16, np.int32])
def test_dtype(dtype):
    # test dtype i/o
    x = np.random.randn(100).astype(dtype)

    y = soxr.resample(x, 100, 200)

    assert x.dtype == y.dtype


@pytest.mark.parametrize('dtype', [np.complex64, np.complex128, np.int8, np.int64])
def test_bad_dtype(dtype):
    # test invalid dtype
    x = np.zeros(100, dtype=dtype)
    with pytest.raises((TypeError, ValueError)):
        soxr.resample(x, 100, 200)


@pytest.mark.parametrize('in_rate, out_rate', [(44100, 32000), (32000, 44100)])
@pytest.mark.parametrize('dtype', [np.float32, np.float64])
def test_divide_match(in_rate, out_rate, dtype):
    # test resample()
    x = np.random.randn(25999,2).astype(dtype)

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)
    y_divide = soxr.resample(x, in_rate, out_rate)
    y_split = soxr.resample(np.asfortranarray(x), in_rate, out_rate)

    assert np.all(y_oneshot == y_divide)
    assert np.all(y_oneshot == y_split)


@pytest.mark.parametrize('in_rate, out_rate', [(44100, 32000), (32000, 44100)])
@pytest.mark.parametrize('length', [0, 1, 2, 99, 100, 101, 31999, 32000, 32001, 34828, 34829, 34830, 44099, 44100, 44101, 47999, 48000, 48001, 66149, 66150, 266151])
def test_length_match(in_rate, out_rate, length):
    # test sliced array with various length
    x = np.random.randn(266151, 2).astype(np.float32)

    y_oneshot = soxr._resample_oneshot(x[:length], in_rate, out_rate)
    y_divide = soxr.resample(x[:length], in_rate, out_rate)
    y_split = soxr.resample(np.asfortranarray(x)[:length], in_rate, out_rate)

    assert np.all(y_oneshot == y_divide)
    assert np.all(y_oneshot == y_split)


@pytest.mark.parametrize('channels', [1, 2, 3, 5, 7, 24, 49])
def test_channel_match(channels):
    # test sliced array with various channel number
    x = np.random.randn(30011, 49).astype(np.float32)

    y_oneshot = soxr._resample_oneshot(x[:, :channels], 44100, 32000)
    y_divide = soxr.resample(x[:, :channels], 44100, 32000)
    y_split = soxr.resample(np.asfortranarray(x)[:, :channels], 44100, 32000)

    assert np.all(y_oneshot == y_divide)
    assert np.all(y_oneshot == y_split)


def stream_resample(x, in_rate, out_rate, chunk_size, dtype):
    channels = x.shape[1]

    rs_stream = soxr.ResampleStream(in_rate, out_rate, channels, dtype=dtype)

    y_list = [np.ndarray([0, channels], dtype=dtype)]
    for idx in range(0, len(x), chunk_size):
        end = idx + chunk_size
        eof = False
        if len(x) <= end:
            eof = True
            end = len(x)
        y_chunk = rs_stream.resample_chunk(x[idx:end], last=eof)
        y_list.append(y_chunk)

    return np.concatenate(y_list)


@pytest.mark.parametrize('in_rate, out_rate', [(44100, 32000), (32000, 44100)])
@pytest.mark.parametrize('chunk_size', [7, 509, 44100])
@pytest.mark.parametrize('length', [0, 100, 31999, 44100, 266151])
@pytest.mark.parametrize('dtype', ['float32', np.float64])
def test_stream_length(in_rate, out_rate, chunk_size, length, dtype):
    # test resample_chunk() with various length and chunk size
    x = np.random.randn(length, 1).astype(dtype)  # 1ch

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)
    y_stream = stream_resample(x, in_rate, out_rate, chunk_size, dtype)

    assert np.all(y_oneshot == y_stream)


@pytest.mark.parametrize('in_rate, out_rate', [(48000, 22050), (8000, 48000)])
@pytest.mark.parametrize('chunk_size', [50, 101])
@pytest.mark.parametrize('length', [1, 101, 32000, 44101, 49999])
@pytest.mark.parametrize('dtype', ['int32', np.int16])
def test_stream_int(in_rate, out_rate, chunk_size, length, dtype):
    # test int resample_chunk() with various length and chunk size
    x = (np.random.randn(length, 2) * 5000).astype(dtype)   # 2ch

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)
    y_stream = stream_resample(x, in_rate, out_rate, chunk_size, dtype)

    assert np.allclose(y_oneshot, y_stream, atol=2)


def make_tone(freq, sr, duration):
    # make reference tone
    length = int(sr * duration)
    sig = np.sin(2 * np.pi * freq / sr * np.arange(length))
    sig = sig * np.hanning(length)
    
    return np.stack([sig, np.zeros_like(sig)], axis=-1)


@pytest.mark.parametrize('in_rate,out_rate', [(44100, 22050), (22050, 32000)])
@pytest.mark.parametrize('quality', [soxr.VHQ, 'HQ', 'SOXR_MQ', 'lq', 'soxr_qq'])
def test_quality_sine(in_rate, out_rate, quality):
    # compare result with reference
    FREQ = 32.0
    DURATION = 2.0

    x = make_tone(FREQ, in_rate, DURATION)
    y = make_tone(FREQ, out_rate, DURATION)

    y_pred = soxr.resample(x, in_rate, out_rate, quality=quality)
    y_split = soxr.resample(np.asfortranarray(x), in_rate, out_rate, quality=quality)

    assert np.allclose(y, y_pred, atol=1e-4)
    assert np.allclose(y, y_split, atol=1e-4)


@pytest.mark.parametrize('in_rate,out_rate', [(48000, 24000), (32000, 44100)])
@pytest.mark.parametrize('dtype', [np.int32, np.int16])
def test_int_sine(in_rate, out_rate, dtype):
    # compare result with reference (int I/O)
    FREQ = 32.0
    DURATION = 2.0

    x = (make_tone(FREQ, in_rate, DURATION) * 16384).astype(dtype)
    y = (make_tone(FREQ, out_rate, DURATION) * 16384).astype(dtype)

    y_pred = soxr.resample(x, in_rate, out_rate)
    y_split = soxr.resample(np.asfortranarray(x), in_rate, out_rate)
    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)

    assert np.allclose(y, y_pred, atol=2)
    assert np.allclose(y, y_split, atol=2)
    assert np.allclose(y_oneshot, y_pred, atol=2)
    assert np.allclose(y_oneshot, y_split, atol=2)


@pytest.mark.parametrize('num_task', [2, 3, 5, 7, 9, 12, 17, 32])
def test_multithread(num_task):
    # test multi-thread operation
    x = np.random.randn(75999, 2).astype(np.float32)

    with ThreadPoolExecutor() as p:
        results = p.map(
            partial(soxr.resample, in_rate=44100, out_rate=32000),
            [x] * num_task
        )
    results = list(results)

    assert np.all(results[-2] == results[-1])


@pytest.mark.parametrize('num_task', [2, 3, 4, 6, 8, 15, 18, 24])
def test_mt_dither(num_task):
    # test dithering randomness and multi-thread operation
    x = (np.random.randn(70001, 2) * 5000).astype(np.int16)

    with ThreadPoolExecutor() as p:
        results = p.map(
            partial(soxr.resample, in_rate=32000, out_rate=48000),
            [x] * num_task
        )
    results = list(results)

    assert np.allclose(results[0], results[1], atol=2)

    try:
        assert np.all(results[-2] == results[-1])
    except AssertionError:
        pytest.xfail("Random dithering seed used. May produce slightly different result when using int I/O.")
