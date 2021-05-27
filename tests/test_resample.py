
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


@pytest.mark.parametrize('in_rate, out_rate', [(44100, 32000), (32000, 44100)])
@pytest.mark.parametrize('dtype', [np.float32, np.float64])
def test_divide_match(in_rate, out_rate, dtype):
    x = np.random.randn(49999).astype(dtype)

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)
    y_divide = soxr.resample(x, in_rate, out_rate)

    assert np.allclose(y_oneshot, y_divide)


@pytest.mark.parametrize('in_rate, out_rate', [(44100, 32000), (32000, 44100)])
@pytest.mark.parametrize('dtype', [np.float32, np.float64])
def test_stream_match(in_rate, out_rate, dtype):
    CHUNK_SIZE = 509
    x = np.random.randn(49999).astype(dtype)

    y_oneshot = soxr._resample_oneshot(x, in_rate, out_rate)

    rs_stream = soxr.ResampleStream(in_rate, out_rate, 1, dtype=dtype)

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


def make_tone(freq, sr, duration):
    return np.sin(2 * np.pi * freq / sr * np.arange(int(sr * duration)))


@pytest.mark.parametrize('in_rate,out_rate', [(44100, 22050), (22050, 44100)])
@pytest.mark.parametrize('quality', ['VHQ', 'HQ', 'MQ', 'LQ', 'QQ'])
def test_quality_sine(in_rate, out_rate, quality):
    FREQ = 512.0
    DURATION = 2.0
    x = make_tone(FREQ, in_rate, DURATION)
    y = make_tone(FREQ, out_rate, DURATION)

    y_pred = soxr.resample(x, in_rate, out_rate, quality=quality)

    err = np.mean(np.abs(y-y_pred))
    assert err < 1e-5
