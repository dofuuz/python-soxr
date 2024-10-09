# Python-SoXR

[![GitHub](https://img.shields.io/badge/GitHub-python--soxr-181717?logo=github)](https://github.com/dofuuz/python-soxr) [![PyPI](https://img.shields.io/pypi/v/soxr.svg?logo=pypi)](https://pypi.org/project/soxr/) [![conda-forge](https://img.shields.io/conda/vn/conda-forge/soxr-python?logo=conda-forge)](https://anaconda.org/conda-forge/soxr-python) [![Packaging status](https://repology.org/badge/tiny-repos/python:soxr.svg)](https://repology.org/project/python:soxr/versions) [![Read the Docs](https://img.shields.io/readthedocs/python-soxr?logo=read-the-docs)](https://python-soxr.readthedocs.io)

High quality, one-dimensional sample-rate conversion library for Python.

- Homepage: https://github.com/dofuuz/python-soxr
- Documentation: https://python-soxr.readthedocs.io
- PyPI: https://pypi.org/project/soxr/

Keywords: Resampler, Audio resampling, Samplerate conversion, DSP(Digital Signal Processing)

Python-SoXR is a Python wrapper of [libsoxr](https://sourceforge.net/projects/soxr/).


## Installation

```sh
pip install soxr
```

If installation fails, upgrade pip with `python -m pip install --upgrade pip` and try again.


### in Conda environment

```sh
conda install -c conda-forge soxr-python
```

Note: Conda packge name is `soxr-python`, not python-soxr.


## Basic usage

```python
import soxr

y = soxr.resample(
    x,          # input array – mono(1D) or multi-channel(2D of [frame, channel])
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
        x,              # input aray – mono(1D) or multi-channel(2D of [frame, channel])
        last=eof        # Set True at end of input
    )
```

Output frame count may not be consistent. This is normal operation.  
(ex. [0, 0, 0, 186, 186, 166, 186, 186, 168, ...])

📝 [More code examples](https://dofuuz.github.io/dsp/2024/05/26/sample-rate-conversion-in-python.html)


## Benchmark

Sweep, impulse, speed compairsion with other resamplers for Python.

https://colab.research.google.com/drive/1_xYUs00VWYOAXShB85W1MFWaUjGHfO4K?usp=sharing


### Speed comparison summary

Downsampling 10 sec of 48000 Hz to 44100 Hz.  
Ran on Google Colab.

Library                  | Time on CPU (ms)
------------------------ | ----------------
soxr (HQ)                | 10.8
torchaudio               | 13.8
soxr (VHQ)               | 14.5
scipy.signal.resample    | 21.3
lilfilter                | 24.7
julius                   | 31
resampy (kaiser_fast)    | 108
samplerate (sinc_medium) | 223
resampy (kaiser_best)    | 310
samplerate (sinc_best)   | 794


## Technical detail

For technical details behind resampler, see libsoxr docs.
- https://sourceforge.net/p/soxr/wiki/Home/
- http://sox.sourceforge.net/SoX/Resampling ([archive](https://web.archive.org/web/20230626144127/https://sox.sourceforge.net/SoX/Resampling))
- https://sourceforge.net/p/soxr/code/ci/master/tree/src/soxr.h

Python-SoXR package comes with [modified version](https://github.com/dofuuz/soxr) of libsoxr. [See changes here](https://github.com/dofuuz/soxr/compare/0.1.3...master).  
These changes do not apply to dynamic-linked builds (e.g. conda-forge build).  
To check the version of libsoxr, use `soxr.__libsoxr_version__`.


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
