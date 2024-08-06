# -*- coding: utf-8 -*-
"""
Created on Wed Apr 13 00:33:32 2022

@author: dof
"""

import asyncio
from time import time

import numpy as np
import soxr


# generate 150s 2ch data
fs = 44100
ch1 = np.sin(np.linspace(0, fs, 150 * 44100))
ch2 = np.cos(np.linspace(0, fs, 150 * 44100))
data = np.stack([ch1, ch2], axis=-1)
print(data.shape)


def resample():
    soxr.resample(data, fs, 24000)


async def th_resample():
    await asyncio.to_thread(resample)


async def main():
    t = time()
    resample()
    print(time() - t)

    t = time()
    await asyncio.gather(th_resample())
    print(time() - t)

    t = time()
    await asyncio.gather(th_resample(), th_resample())
    print(time() - t)

    t = time()
    await asyncio.gather(th_resample(), th_resample(), th_resample())
    print(time() - t)

    t = time()
    await asyncio.gather(th_resample(), th_resample(), th_resample(), th_resample())
    print(time() - t)

    t = time()
    await asyncio.gather(th_resample(), th_resample(), th_resample(), th_resample(), th_resample())
    print(time() - t)


asyncio.run(main())
