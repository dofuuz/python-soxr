# Building Python-SoXR

## Preparation
```
# Upgrade PIP
python -m pip install --upgrade pip

# Clone code including submodule
git clone --recurse-submodules https://github.com/dofuuz/python-soxr.git

cd python-soxr
```


## Build package(wheel)
```
pip wheel -v .
```

### (Alternative method) Build using system libsoxr
libsoxr should be installed before building.  
(e.g. `sudo apt install libsoxr-dev`)
```
export CMAKE_ARGS="-DUSE_SYSTEM_LIBSOXR=ON"
pip wheel -v .
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
python -m pytest
```
