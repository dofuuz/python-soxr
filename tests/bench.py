# -*- coding: utf-8 -*-
"""
Python-SoXR
https://github.com/dofuuz/python-soxr

SPDX-FileCopyrightText: (c) 2021 Myungchul Keum
SPDX-License-Identifier: LGPL-2.1-or-later

Simple speed benchmark for Python-SoXR.
"""

import timeit

import numpy as np

import soxr

LEN = 96000
REPEAT = 1000
P = 48000
Q = 44100

QUALITY = 'HQ'
CHUNK_SIZE = int(P * 0.01)


print(f'{soxr.__version__ = }')
print(f'{soxr.__libsoxr_version__ = }')
print(f'{QUALITY = }')

# generate signal
offset = 2000
instfreq = np.exp(np.linspace(np.log(offset+100), np.log(offset+23900), LEN))-offset
deltaphase = 2*np.pi*instfreq/P
cphase = np.cumsum(deltaphase)
sig = np.sin(cphase)
sig = np.stack([sig, sig, sig, sig], axis=-1, dtype=np.float64)
print(f'{sig.shape = }')


# soxr oneshot (test purpose only)
t = timeit.timeit(lambda: soxr._resample_oneshot(sig, P, Q, quality=QUALITY), number=REPEAT)
print(f'soxr oneshot: {t:f} (sec)')


# soxr resample
t = timeit.timeit(lambda: soxr.resample(sig, P, Q, quality=QUALITY), number=REPEAT)
print(f'soxr resample: {t:f} (sec)')


# soxr split ch I/O:
sig_s = np.asfortranarray(sig)
t = timeit.timeit(lambda: soxr.resample(sig_s, P, Q, quality=QUALITY), number=REPEAT)
print(f'soxr split ch I/O: {t:f} (sec)')


# soxr with clear()
# It becomes faster then soxr.resample() when input length (=LEN) is short
rs = soxr.ResampleStream(P, Q, sig.shape[1], dtype=sig.dtype, quality=QUALITY)

def soxr_with_reset():
    rs.clear()
    return rs.resample_chunk(sig, last=True)

t = timeit.timeit(soxr_with_reset, number=REPEAT)
print(f'soxr w/ clear(): {t:f} (sec)')


# soxr stream chunk processing
def soxr_stream():
    rs_stream = soxr.ResampleStream(P, Q, sig.shape[1], dtype=sig.dtype, quality=QUALITY)

    y_list = []
    for idx in range(0, len(sig), CHUNK_SIZE):
        end = idx + CHUNK_SIZE
        eof = False
        if len(sig) <= end:
            eof = True
            end = len(sig)
        y_chunk = rs_stream.resample_chunk(sig[idx:end], last=eof)
        y_list.append(y_chunk)

    return np.concatenate(y_list)

t = timeit.timeit(soxr_stream, number=REPEAT)
print(f'{CHUNK_SIZE = }')
print(f'soxr stream: {t:f} (sec)')


# resampy kaiser_fast
try:
    import resampy

    t = timeit.timeit(lambda: resampy.resample(sig.T, P, Q, filter='kaiser_fast'), number=REPEAT)
    print(f'resampy kaiser_fast: {t:f} (sec)')
except ModuleNotFoundError:
    pass
