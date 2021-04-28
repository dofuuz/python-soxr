from setuptools import find_packages
from setuptools import setup, Extension


with open("README.md", "r") as fh:
    long_description = fh.read()


class CySoxrExtension(Extension):
    def __init__(self, *args, **kwargs):
        self._include = []
        super().__init__(*args, **kwargs)

    @property
    def include_dirs(self):
        import numpy
        return self._include + [numpy.get_include()]

    @include_dirs.setter
    def include_dirs(self, dirs):
        self._include = dirs

src = [
    'libsoxr/src/soxr.c',
    'libsoxr/src/data-io.c',
    'libsoxr/src/dbesi0.c',
    'libsoxr/src/filter.c',
    'libsoxr/src/fft4g64.c',
    'libsoxr/src/cr.c',
    'libsoxr/src/cr32.c',
    'libsoxr/src/fft4g32.c',
    'libsoxr/src/cr64.c',
    'libsoxr/src/vr32.c',
    'libsoxr/src/cr32s.c',
    'libsoxr/src/pffft32s.c',
    'libsoxr/src/util32s.c',
    'libsoxr/src/cr64s.c',
    'libsoxr/src/pffft64s.c',
    'libsoxr/src/util64s.c',
    'csoxr.pxd',
    'cysoxr.pyx'
]

extensions = [
    CySoxrExtension(
        "cysoxr",
        src,
        include_dirs=['libsoxr/src', 'libsoxr/msvc'],
        language="c",
        extra_compile_args=['-DSOXR_LIB'])
]
setup(
    name="soxr",
    version="0.0.1",
    author="dofuuz",
    description="Python Wrapper for libsoxr",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dofuuz/python-soxr",
    packages=find_packages(),
    package_data={'soxr':["*.pyx", "*.h"]},
    ext_package='soxr',
    ext_modules=extensions,
    setup_requires=['setuptools>=18.0', 'cython', 'numpy', 'pytest-runner'],
    tests_require=['pytest'],
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
        "Operating System :: OS Independent",
    ]
)
