# Building Python-SoXR

## Preparation
```
# Upgrade PIP
python -m pip install --upgrade pip

# Clone code including submodule
git clone --recurse-submodules https://github.com/dofuuz/python-soxr.git
```


## Build package(wheel)
```
cd python-soxr
pip wheel -ve .
```

### (Alternative method) Build using system libsoxr
libsoxr should be installed before building.  
(e.g. `sudo apt install libsoxr-dev`)
```
export CMAKE_ARGS="-DUSE_SYSTEM_LIBSOXR=ON"
pip wheel -ve .
```
It will link libsoxr dynamically and won't bundle libsoxr in the wheel package.


## Install
Install built .whl package(not .tar.gz sdist).
```
pip install ./soxr-[...].whl
```


## Test
```
# Install dependencies
pip install pytest

# Test (using installed Python-SoXR)
cd python-soxr/tests
python -m pytest
```
