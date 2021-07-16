# Building Python-SoXR

## Preparation
```
# Clone code including submodule
git clone --recurse-submodules https://github.com/dofuuz/python-soxr.git

# Upgrade PIP
python -m pip install --upgrade pip
```

## Build
```
# Install dependencies
pip install "setuptools>=42" wheel "Cython>=3.0a7" numpy

# Build
cd python-soxr
python setup.py build
```

## Test
```
# Install dependencies
pip install pytest

# Test (using installed Python-SoXR)
cd python-soxr/tests
python -m pytest
```

## Build package(wheel)
```
# Install dependencies
pip install build

# Build wheel
cd python-soxr
python -m build
```
