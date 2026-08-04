from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from shutil import rmtree

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py

HERE = Path(__file__).resolve().parent
BUILD_DATA_SPEC = spec_from_file_location('openccfontgenerator_build_data', HERE / 'build_data.py')
BUILD_DATA_MODULE = module_from_spec(BUILD_DATA_SPEC)
BUILD_DATA_SPEC.loader.exec_module(BUILD_DATA_MODULE)

class BuildPy(build_py):
    def run(self):
        package_build_dir = (Path(self.build_lib) / 'OpenCCFontGenerator').resolve()
        source_package_dir = (HERE / 'src' / 'OpenCCFontGenerator').resolve()
        if package_build_dir == source_package_dir or package_build_dir.name != 'OpenCCFontGenerator':
            raise RuntimeError(f'unsafe package build directory: {package_build_dir}')
        for directory_name in ('cache', 'opencc_data', 'generated'):
            stale_directory = package_build_dir / directory_name
            if stale_directory.is_symlink():
                raise RuntimeError(f'unsafe package build directory link: {stale_directory}')
            if stale_directory.is_dir():
                rmtree(stale_directory)
        super().run()
        BUILD_DATA_MODULE.build_data(Path(self.build_lib) / 'OpenCCFontGenerator' / 'generated')

setup(
    name='OpenCCFontGenerator',
    version='0.1.0',
    description='Generate OpenType fonts backed by OpenCC conversion data',
    long_description=(HERE / 'README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    url='https://github.com/ayaka14732/OpenCCFontGenerator',
    author='ayaka14732',
    author_email='ayaka@mail.shn.hk',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Linguistic',
        'Natural Language :: Chinese (Simplified)',
        'Natural Language :: Chinese (Traditional)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.14',
    ],
    keywords='chinese nlp natural-language-processing font opentype opencc',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'OpenCCFontGenerator': ['*.json', '*.txt', *(f'generated/{filename}' for filename in BUILD_DATA_MODULE.GENERATED_FILENAMES)]},
    include_package_data=True,
    python_requires='>=3.14',
    cmdclass={'build_py': BuildPy},
    project_urls={
        'Bug Reports': 'https://github.com/ayaka14732/OpenCCFontGenerator/issues',
        'Source': 'https://github.com/ayaka14732/OpenCCFontGenerator',
    },
    zip_safe=False,
)
