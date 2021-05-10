# Python-SoXR

High quality, one-dimensional sample-rate conversion library for Python


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
Output is 2D numpy.ndarray with shape (frames, channels).


## Credits

### libsoxr (LGPLv2.1+)
https://sourceforge.net/projects/soxr/  
Python-SoXR is a Python wrapper of libsoxr


### PFFFT (BSD-like)
https://bitbucket.org/jpommier/pffft/  
libsoxr uses PFFFT as FFT
