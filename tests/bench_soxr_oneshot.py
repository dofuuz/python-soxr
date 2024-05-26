# -*- coding: utf-8 -*-
"""
Python-SoXR
https://github.com/dofuuz/python-soxr

SPDX-FileCopyrightText: (c) 2021 Myungchul Keum
SPDX-License-Identifier: LGPL-2.1-or-later

soxr_oneshot() becomes much slower when input is long.
This script demonstrates it.

soxr.resample() divides input automatically to retain speed.
"""

import time

import matplotlib.pyplot as plt
import numpy as np
import soxr


P = 48000
Q = 44100


# generate signal
offset = 2000
instfreq = np.exp(np.linspace(np.log(offset+100), np.log(offset+23900), 96000*5))-offset
deltaphase = 2*np.pi*instfreq/P
cphase = np.cumsum(deltaphase)
sig = np.sin(cphase)
sig = np.asarray([sig, sig, sig, sig], dtype=np.float64).T


out_lens = []
time_divide = []
time_oneshot = []
for length in range(4800, len(sig), 4800):
    # soxr resample
    start_time = time.perf_counter()
    y_resample = soxr.resample(sig[:length], P, Q)
    time_proc = time.perf_counter() - start_time
    time_divide.append(time_proc)

    # soxr oneshot
    start_time = time.perf_counter()
    y_oneshot = soxr._resample_oneshot(sig[:length], P, Q)
    time_proc = time.perf_counter() - start_time
    time_oneshot.append(time_proc)
    out_lens.append(len(y_oneshot))

plt.plot(out_lens, time_oneshot)
plt.plot(out_lens, time_divide)
