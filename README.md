# Python-SoXR

[![GitHub](https://img.shields.io/badge/GitHub-python--soxr-181717?logo=github)](https://github.com/dofuuz/python-soxr) [![PyPI](https://img.shields.io/pypi/v/soxr.svg?logo=pypi)](https://pypi.org/project/soxr/) [![Read the Docs](https://img.shields.io/readthedocs/python-soxr?logo=read-the-docs)](https://python-soxr.readthedocs.io)

High quality, one-dimensional sample-rate conversion library for Python.

- Homepage: https://github.com/dofuuz/python-soxr
- Documentation: https://python-soxr.readthedocs.io
- PyPI: https://pypi.org/project/soxr/

Python-SoXR is a Python wrapper of [libsoxr](https://sourceforge.net/projects/soxr/).


## Installation

```
pip install soxr
```

If installation fails, upgrade pip with `python -m pip install --upgrade pip` and try again.


## Basic usage

```python
import soxr

y = soxr.resample(
    x,          # 1D(mono) or 2D(frames, channels) array input
    48000,      # input samplerate
    16000       # target samplerate
)
```
If input is not `numpy.ndarray`, it will be converted to `numpy.ndarray(dtype='float32')`.  
dtype should be one of float32, float64, int16, int32.

Output is `numpy.ndarray` with same dimension and data type of input.


## Streaming usage

Use `ResampleStream` for real-time processing or very long signal.

```python
import soxr

rs = soxr.ResampleStream(
    44100,              # input samplerate
    16000,              # target samplerate
    1,                  # channel(s)
    dtype='float32'     # data type (default = 'float32')
)

eof = False
while not eof:
    # Get chunk
    ...

    y_chunk = rs.resample_chunk(
        x,              # 1D(mono) or 2D(frames, channels) array input
        last=eof        # Set True at end of input
    )
```

Output frame count may not be consistent. This is normal operation.  
(ex. [0, 0, 0, 186, 186, 166, 186, 186, 168, ...])


## Requirement

x86 and ARM processors are supported.

Neon extension is required for ARM CPUs. Without Neon, it may crash or return inaccurate result.


## Benchmark

Sweep, impulse, speed compairsion with other Python resamplers.

https://colab.research.google.com/drive/1XgSOvWlRIau1FYwQG_yRSAhDK3KB8bEL?usp=sharing


### Speed comparison summary

Downsampling 10 sec of 48000 Hz to 44100 Hz.  
Ran on Google Colab.

Library                  | Time on CPU (ms)
------------------------ | ----------------
soxr (HQ)                | 7.2
scipy.signal.resample    | 13.4
soxr (VHQ)               | 15.8
torchaudio               | 19.2
lilfilter                | 21.4
julius                   | 23.1
resampy (kaiser_fast)    | 62.6
samplerate (sinc_medium) | 92.5
resampy (kaiser_best)    | 256
samplerate (sinc_best)   | 397


## Technical detail

For technical details behind resampler, see libsoxr docs.
- https://sourceforge.net/p/soxr/wiki/Home/
- http://sox.sourceforge.net/SoX/Resampling
- https://sourceforge.net/p/soxr/code/ci/master/tree/src/soxr.h


## Credit and License

Python-SoXR is LGPL v2.1+ licensed, following libsoxr's license.

### OSS libraries used

#### libsoxr (LGPLv2.1+)
The SoX Resampler library  
https://sourceforge.net/projects/soxr/

Python-SoXR is a Python wrapper of libsoxr.

#### PFFFT (BSD-like)
PFFFT: a pretty fast FFT.  
https://bitbucket.org/jpommier/pffft/  

libsoxr dependency.
