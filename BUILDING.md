# Building Python-SoXR

## Preparation
```
# Clone code including submodule
git clone --recurse-submodules https://github.com/dofuuz/python-soxr.git

# Upgrade PIP
python -m pip install --upgrade pip
```


## Build package(wheel)
```
# Install dependencies
pip install build

# Build wheel
python -m build
```


## Test
```
# Install dependencies
pip install pytest

# Test (using installed Python-SoXR)
cd python-soxr/tests
python -m pytest
```
