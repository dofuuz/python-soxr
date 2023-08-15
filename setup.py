"""
Python-SoXR setup.py for Cython build

Please refer to BUILDING.md for building instructions.
Do not run setup.py directly for the build process.
"""

import logging
import subprocess
import sys
import sysconfig

from distutils.ccompiler import get_default_compiler
from setuptools import setup, Extension
from setuptools.command.sdist import sdist


SYS_LIBSOXR = False

# python -m build -C=--build-option=--use-system-libsoxr
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


def get_git_version(cwd=''):
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--always', '--dirty'],
            cwd=cwd, capture_output=True, check=True, text=True)

        ver = result.stdout.strip()
        return ver
    except Exception as e:
        logging.warning(f'Error retrieving submodule version: {e}')
    return 'unknown'


def write_submodule_version(name, path):
    ver = get_git_version(path)
    with open(f'src/soxr/_{name}_version.py', 'wt') as f:
        f.write(f'__{name}_version__ = "{ver}"')
    logging.info(f'{name} version: {ver}')


class SDistBundledCommand(sdist):
    def run(self):
        write_submodule_version('libsoxr', 'libsoxr')
        super().run()


LIBSOXR_VERSION_PY = '''
from .cysoxr import libsoxr_version
__libsoxr_version__ = libsoxr_version()
'''

class SDistDynamicCommand(sdist):
    def run(self):
        with open('src/soxr/_libsoxr_version.py', 'wt') as f:
            f.write(LIBSOXR_VERSION_PY)
        super().run()


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

platform = sysconfig.get_platform()
if '-arm' in platform:
    compile_args.append('-mfpu=neon')
elif '-i686' in platform:
    compile_args.append('-msse')

if get_default_compiler() in ['unix', 'mingw32']:
    compile_args += ['-std=gnu99', '-Werror=implicit']

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
        logging.info('Building Python-SoXR using system libsoxr...')
        setup(
            cmdclass={'sdist': SDistDynamicCommand},
            ext_modules=cythonize(extensions_dynamic, language_level='3'),
        )
    else:
        logging.info('Building Python-SoXR using bundled libsoxr...')
        setup(
            cmdclass={'sdist': SDistBundledCommand},
            ext_modules=cythonize(extensions, language_level='3'),
        )
