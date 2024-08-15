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

import timeit

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
sig1 = np.sin(cphase)
sig2 = np.cos(cphase)
sig_i = np.stack([sig1, sig2, sig1, sig2], axis=-1, dtype=np.float64)  # C memory order (interleaved)
sig_s = np.asarray([sig1, sig2, sig1, sig2], dtype=np.float64).T  # Fortran memory order (channel splited)


in_lens = range(4800, len(sig1), 4800)
time_divide = []
time_oneshot = []
time_split = []
for length in in_lens:
    # soxr resample
    time_proc = timeit.timeit(lambda: soxr.resample(sig_i[:length], P, Q), number=2)
    time_divide.append(time_proc)

    # soxr resample w/ split channel I/O
    time_proc = timeit.timeit(lambda: soxr.resample(sig_s[:length], P, Q), number=2)
    time_split.append(time_proc)

    # soxr oneshot
    time_proc = timeit.timeit(lambda: soxr._resample_oneshot(sig_i[:length], P, Q), number=2)
    time_oneshot.append(time_proc)

plt.plot(in_lens, time_divide, label='divide')
plt.plot(in_lens, time_split, label='split ch')
plt.plot(in_lens, time_oneshot, label='oneshot')
plt.legend()
plt.show()
