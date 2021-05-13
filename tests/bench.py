# -*- coding: utf-8 -*-
"""
Created on Fri May  7 21:40:53 2021

@author: dof
"""

import time

import numpy as np

import resampy
import soxr


P = 48000
Q = 44100

CHUNK_SIZE = int(P * 0.01)


# generate signal
offset = 2000
instfreq = np.exp(np.linspace(np.log(offset+100), np.log(offset+23900), 96000))-offset
deltaphase = 2*np.pi*instfreq/P
cphase = np.cumsum(deltaphase)
sig = np.sin(cphase, dtype=np.float32)


# soxr oneshot
start_time = time.perf_counter()
y_oneshot = soxr._resample_oneshot(sig, P, Q)
print('soxr oneshot: {:f} (sec), {}'.format(
    time.perf_counter() - start_time,
    y_oneshot.shape))


# soxr resample
start_time = time.perf_counter()
y_resample = soxr.resample(sig, P, Q)
print('soxr resample: {:f} (sec), {}'.format(
    time.perf_counter() - start_time,
    y_resample.shape))


# soxr stream
start_time = time.perf_counter()

rs_stream = soxr.ResampleStream(P, Q, 1, dtype=sig.dtype)

y_list = []
for idx in range(0, len(sig), CHUNK_SIZE):
    end = idx + CHUNK_SIZE
    eof = False
    if len(sig) <= end:
        eof = True
        end = len(sig)
    y_chunk = rs_stream.resample_chunk(sig[idx:end], last=eof)
    y_list.append(y_chunk)

y_stream = np.concatenate(y_list)

print('soxr stream: {:f} (sec), {}'.format(
    time.perf_counter() - start_time,
    y_stream.shape))


# resampy kaiser_fast
start_time = time.perf_counter()
y_resampy = resampy.resample(sig.T, P, Q, filter='kaiser_fast')
print('resampy kaiser_fast: {:f} (sec), {}'.format(
    time.perf_counter() - start_time,
    y_resampy.shape))
