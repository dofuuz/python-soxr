"""
Python-SoXR
https://github.com/dofuuz/python-soxr

SPDX-FileCopyrightText: (c) 2021 Myungchul Keum
SPDX-License-Identifier: LGPL-2.1-or-later

High quality, one-dimensional sample-rate conversion library for Python.
Python-SoXR is a Python wrapper of libsoxr.
"""

import random
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import numpy as np
import pytest
import soxr


def get_random_sr_pairs():
    return [
        (random.randint(8000, 96000), random.randint(8000, 96000)),
        (random.uniform(8000, 96000), random.uniform(8000, 96000)),
    ]


@pytest.mark.parametrize('in_rate, out_rate', [
    (random.randint(0, 192000), 0),
    (random.randint(0, 192000), random.randint(-192000, 0)),
    (0, random.uniform(0, 192000)),
    (random.uniform(-192000, 0), random.randint(0, 192000)),
])
def test_bad_sr(in_rate, out_rate):
    # test invalid samplerate
    x = np.zeros(100)
    with pytest.raises(ValueError):
        soxr.resample(x, in_rate, out_rate)


@pytest.mark.parametrize('in_rate, out_rate', get_random_sr_pairs())
@pytest.mark.parametrize('frames', [random.randint(1, 50000)])
@pytest.mark.parametrize('dtype', [np.float32, np.float64])
def test_divide_match(in_rate, out_rate, frames, dtype):
    # test resample() with a randomized shape
    x = np.random.randn(frames, 2).astype(dtype)

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)
    y_divide = soxr.resample(x, in_rate, out_rate)
    y_split = soxr.resample(np.asfortranarray(x), in_rate, out_rate)

    assert np.all(y_oneshot == y_divide)
    assert np.all(y_oneshot == y_split)


@pytest.mark.parametrize('in_rate, out_rate', get_random_sr_pairs())
@pytest.mark.parametrize('length', [0, 1] + [random.randint(2, 150000) for _ in range(6)])
@pytest.mark.parametrize('arr_len', [random.randint(150000, 300000)])
def test_length_match(in_rate, out_rate, length, arr_len):
    # test sliced array with various length
    x = np.random.randn(arr_len, 2).astype(np.float32)

    y_oneshot = soxr._resample_oneshot(x[:length], in_rate, out_rate)
    y_divide = soxr.resample(x[:length], in_rate, out_rate)
    y_split = soxr.resample(np.asfortranarray(x)[:length], in_rate, out_rate)

    assert np.all(y_oneshot == y_divide)
    assert np.all(y_oneshot == y_split)


@pytest.mark.parametrize('frames', [random.randint(1, 10000)])
@pytest.mark.parametrize('channels', [1] + random.sample(range(2, 64), 6))
def test_channel_match(frames, channels):
    # test sliced array with various channel number
    x = np.random.randn(frames, 64).astype(np.float32)

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


@pytest.mark.parametrize('in_rate, out_rate', get_random_sr_pairs())
@pytest.mark.parametrize('chunk_size', [random.randint(5, 50000) for _ in range(2)])
@pytest.mark.parametrize('length', [0] + [random.randint(2, 150000) for _ in range(4)])
@pytest.mark.parametrize('dtype', ['float32', np.float64])
def test_stream_length(in_rate, out_rate, chunk_size, length, dtype):
    # test resample_chunk() with various length and chunk size
    x = np.random.randn(length, 1).astype(dtype)  # 1ch

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)
    y_stream = stream_resample(x, in_rate, out_rate, chunk_size, dtype)

    assert np.all(y_oneshot == y_stream)


@pytest.mark.parametrize('in_rate, out_rate', get_random_sr_pairs())
@pytest.mark.parametrize('chunk_size', [random.randint(5, 5000) for _ in range(3)])
@pytest.mark.parametrize('length', [1] + [random.randint(2, 30000) for _ in range(4)])
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
    
    return sig


@pytest.mark.parametrize('in_rate,out_rate', get_random_sr_pairs())
@pytest.mark.parametrize('quality', [soxr.VHQ, 'HQ', 'SOXR_MQ', 'lq', 'soxr_qq'])
def test_quality_sine(in_rate, out_rate, quality):
    # compare result with reference
    FREQ = 32.0
    DURATION = 4.0

    x = make_tone(FREQ, in_rate, DURATION)
    y = make_tone(FREQ, out_rate, DURATION)

    y_pred = soxr.resample(x, in_rate, out_rate, quality=quality)
    y_split = soxr.resample(np.asfortranarray(x), in_rate, out_rate, quality=quality)

    min_len = min(len(y), len(y_pred))

    # some rate combination makes error bigger
    assert np.allclose(y[:min_len], y_pred[:min_len], atol=2e-4)
    assert np.allclose(y[:min_len], y_split[:min_len], atol=2e-4)


@pytest.mark.parametrize('in_rate,out_rate', get_random_sr_pairs())
@pytest.mark.parametrize('dtype', [np.int32, np.int16])
def test_int_sine(in_rate, out_rate, dtype):
    # compare result with reference (int I/O)
    FREQ = 32.0
    DURATION = 4.0

    x = (make_tone(FREQ, in_rate, DURATION) * 16384).astype(dtype)
    y = (make_tone(FREQ, out_rate, DURATION) * 16384).astype(dtype)

    y_pred = soxr.resample(x, in_rate, out_rate)
    y_split = soxr.resample(np.asfortranarray(x), in_rate, out_rate)
    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)

    min_len = min(len(y), len(y_pred))

    # some rate combination makes error bigger
    assert np.allclose(y[:min_len], y_pred[:min_len], atol=5)
    assert np.allclose(y[:min_len], y_split[:min_len], atol=5)
    assert np.allclose(y_oneshot, y_split, atol=2)


@pytest.mark.parametrize('num_task', random.sample(range(2, 40), 6))
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


@pytest.mark.parametrize('num_task', random.sample(range(2, 40), 6))
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


def get_random_vr_sr_pairs():
    # limit rate ratio under 4. VR timing error gets bigger with higher ratio
    return [
        (random.randint(24000, 96000), random.randint(24000, 96000)),
        (random.uniform(24000, 96000), random.uniform(24000, 96000)),
    ]


@pytest.mark.parametrize('in_rate,out_rate', get_random_vr_sr_pairs())
@pytest.mark.parametrize('dtype', [np.float32, np.float64, np.int32, np.int16])
def test_vr_sine(in_rate, out_rate, dtype):
    # VR mode: change I/O ratio on the way and compare result with reference
    FREQ = 32.0
    DURATION = 4.0
    scale = 16384 if np.issubdtype(dtype, np.integer) else 1

    x1 = (make_tone(FREQ, in_rate, DURATION) * scale).astype(dtype)
    x2 = (make_tone(FREQ, out_rate, DURATION) * scale).astype(dtype)
    y1 = (make_tone(FREQ, out_rate, DURATION) * scale).astype(dtype)
    y2 = (make_tone(FREQ, in_rate, DURATION) * scale).astype(dtype)

    rs = soxr.ResampleStream(4, 1, 1, dtype=dtype, vr=True)     # max I/O ratio: 4
    rs.set_io_ratio(in_rate, out_rate)
    y1_pred = rs.resample_chunk(x1)
    rs.set_io_ratio(out_rate, in_rate)
    y2_pred = rs.resample_chunk(x2, last=True)

    y = np.concatenate([y1, y2])
    y_pred = np.concatenate([y1_pred, y2_pred])

    # Input pending at set_io_ratio() is resampled with new ratio. So length differs slightly.
    # Compare y1 from the start and y2 from the end. (VR engine has ~2 samples of delay)
    assert y_pred.dtype == y.dtype
    assert abs(len(y_pred) - len(y)) < 0.03 * len(y)
    assert np.allclose(y1, y_pred[:len(y1)], atol=0.05 * scale)
    assert np.allclose(y2, y_pred[-len(y2):], atol=0.05 * scale)


@pytest.mark.parametrize('io_ratio', [random.uniform(0.25, 4)])
@pytest.mark.parametrize('chunk_size', [1] + [random.randint(2, 5000) for _ in range(3)])
@pytest.mark.parametrize('length', [random.randint(2, 30000)])
def test_vr_chunk_match(io_ratio, chunk_size, length):
    # VR output should not depend on chunk size
    # (Not tested with ratio change. It makes tiny difference when jumping over 2 octaves)
    x = np.random.randn(length, 2).astype(np.float32)

    def run(chunk):
        rs = soxr.ResampleStream(4, 1, 2, vr=True)
        rs.set_io_ratio(io_ratio, 1)
        y_list = [rs.resample_chunk(x[i:i + chunk]) for i in range(0, length, chunk)]
        y_list.append(rs.resample_chunk(x[:0], last=True))
        return np.concatenate(y_list)

    y_whole = run(length)
    y_chunk = run(chunk_size)

    assert y_whole.shape == y_chunk.shape
    assert np.all(y_whole == y_chunk)
