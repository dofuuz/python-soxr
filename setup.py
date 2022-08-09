import sys

from setuptools import find_packages
from setuptools import setup, Extension

import distutils.util


SYS_LIBSOXR = False

# python -m build -C=--global-option=--use-system-libsoxr
if '--use-system-libsoxr' in sys.argv:
    sys.argv.remove('--use-system-libsoxr')
    SYS_LIBSOXR = True


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

src_libsoxr = [
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
]

src = [
    # Cython wrapper
    'src/soxr/cysoxr.pyx'
]

compile_args = ['-DSOXR_LIB']
platform = distutils.util.get_platform()

if '-arm' in platform:
    compile_args.append('-mfpu=neon')
elif '-i686' in platform:
    compile_args.append('-msse')

extensions = [
    CySoxrExtension(
        "soxr.cysoxr",
        src_libsoxr + src,
        include_dirs=['libsoxr/src', 'src/soxr'],
        language="c",
        extra_compile_args=compile_args)
]

extensions_dynamic = [
    CySoxrExtension('soxr.cysoxr', src, language='c', libraries=['soxr'])
]


if __name__ == "__main__":
    from Cython.Build import cythonize

    if SYS_LIBSOXR:
        setup(
            ext_modules=cythonize(extensions_dynamic, language_level='3'),
        )
    else:
        setup(
            ext_modules=cythonize(extensions, language_level='3'),
        )
