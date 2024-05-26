# -*- coding: utf-8 -*-
"""
Python-SoXR
https://github.com/dofuuz/python-soxr

SPDX-FileCopyrightText: (c) 2021 Myungchul Keum
SPDX-License-Identifier: LGPL-2.1-or-later

High quality, one-dimensional sample-rate conversion library for Python.
Python-SoXR is a Python wrapper of libsoxr.
"""

import timeit

import numpy as np

import soxr

REPEAT = 1000
P = 48000
Q = 44100

CHUNK_SIZE = int(P * 0.01)


# generate signal
offset = 2000
instfreq = np.exp(np.linspace(np.log(offset+100), np.log(offset+23900), 96000))-offset
deltaphase = 2*np.pi*instfreq/P
cphase = np.cumsum(deltaphase)
sig = np.sin(cphase)
sig = np.asarray([sig, sig, sig, sig], dtype=np.float64).T


# soxr oneshot
t = timeit.timeit(lambda: soxr._resample_oneshot(sig, P, Q), number=REPEAT)
print(f'soxr oneshot: {t:f} (sec)')


# soxr resample
t = timeit.timeit(lambda: soxr.resample(sig, P, Q), number=REPEAT)
print(f'soxr resample: {t:f} (sec)')


# soxr stream
def soxr_stream():
    rs_stream = soxr.ResampleStream(P, Q, sig.shape[1], dtype=sig.dtype)

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
print(f'soxr stream: {t:f} (sec)')


# resampy kaiser_fast
try:
    import resampy

    t = timeit.timeit(lambda: resampy.resample(sig.T, P, Q, filter='kaiser_fast'), number=REPEAT)
    print(f'resampy kaiser_fast: {t:f} (sec)')
except ModuleNotFoundError:
    pass
