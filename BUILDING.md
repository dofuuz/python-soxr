# Building Python-SoXR

## Preparation
```
# Upgrade PIP
python -m pip install --upgrade pip

# Install dependencies
pip install build

# Clone code including submodule
git clone --recurse-submodules https://github.com/dofuuz/python-soxr.git
```


## Build package(wheel)
```
cd python-soxr
python -m build
```

### (Alternative method) Build using system libsoxr
libsoxr should be installed before building.  
(e.g. `sudo apt install libsoxr-dev`)
```
python -m build -C=--global-option=--use-system-libsoxr
```
It will link libsoxr dynamically and libsoxr won't bundled in the wheel package.


## Test
```
# Install dependencies
pip install pytest

# Test (using installed Python-SoXR)
cd python-soxr/tests
python -m pytest
```
