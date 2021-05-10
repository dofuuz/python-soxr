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

    # WITH_CR32
    'libsoxr/src/cr32.c',
    'libsoxr/src/fft4g32.c',

    # WITH_CR64
    'libsoxr/src/cr64.c',

    # WITH_VR32
    # 'libsoxr/src/vr32.c',

    # WITH_CR32S
    'libsoxr/src/cr32s.c',
    'libsoxr/src/pffft32s.c',
    'libsoxr/src/util32s.c',

    # WITH_CR64S
    # 'libsoxr/src/cr64s.c',
    # 'libsoxr/src/pffft64s.c',
    # 'libsoxr/src/util64s.c',

    # Cython wrapper
    'csoxr.pxd',
    'cysoxr.pyx'
]

extensions = [
    CySoxrExtension(
        "cysoxr",
        src,
        include_dirs=['libsoxr/src', 'soxr'],
        language="c",
        extra_compile_args=['-DSOXR_LIB'])
]

setup(
    name="soxr",
    version="0.0.4",
    author="dofuuz",
    description="High quality, one-dimensional sample-rate conversion library",
    keywords='samplerate, SRC',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dofuuz/python-soxr",
    packages=find_packages(),
    ext_package='soxr',
    ext_modules=extensions,
    python_requires='>=3.5',
    install_requires=['numpy'],
    tests_require=['pytest'],
    classifiers=[
        "Development Status :: 3 - Alpha",

        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Telecommunications Industry",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
        "Topic :: Scientific/Engineering",

        "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)",

        "Programming Language :: C",
        "Programming Language :: Python",
    ],
    license_files=['LICENSE.txt'],
)

