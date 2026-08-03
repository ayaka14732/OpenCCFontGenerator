from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).resolve().parent

setup(
    name='OpenCCFontGenerator',
    version='0.1.0',
    description='Generate OpenType fonts backed by OpenCC conversion data',
    long_description=(HERE / 'README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    url='https://github.com/ayaka14732/OpenCCFontGenerator',
    author='ayaka14732',
    author_email='ayaka@mail.shn.hk',
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
    package_data={'OpenCCFontGenerator': ['*.json', '*.txt']},
    include_package_data=True,
    python_requires='>=3.14',
    install_requires=['opencc-py==1.4.1', 'opencc-data==1.4.1'],
    project_urls={
        'Bug Reports': 'https://github.com/ayaka14732/OpenCCFontGenerator/issues',
        'Source': 'https://github.com/ayaka14732/OpenCCFontGenerator',
    },
    zip_safe=False,
)
