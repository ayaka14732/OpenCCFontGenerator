from importlib.metadata import version
from itertools import chain
from os import environ
from pathlib import Path
from urllib.request import urlretrieve

import opencc_data
from opencc import OpenCC

HERE = Path(__file__).resolve().parent
DEFAULT_CACHE_HOME = Path(environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
CACHE_DIR = Path(environ.get('OPENCCFONTGENERATOR_CACHE_DIR', DEFAULT_CACHE_HOME / 'OpenCCFontGenerator')).expanduser()
OPENCC_DATA_VERSION = '1.4.1'
CACHE_SCHEMA_VERSION = 4
CACHE_VERSION = f'opencc-data-{OPENCC_DATA_VERSION}-schema-{CACHE_SCHEMA_VERSION}'
OPENCC_DATA_FILENAMES = (
    'CJK_Compatibility_Ideographs.txt',
    'HKVariants.txt',
    'STCharacters.txt',
    'STPhrases.txt',
    'STPhrases_GeneratedFromRegionalPhrases.txt',
    'TSCharacters.txt',
    'TSCharactersExt.txt',
    'TSPhrases.txt',
    'TWPhrases.txt',
    'TWVariants.txt',
    'TWVariantsPhrases.txt',
)
STANDARD_DICTIONARY_FILENAMES = (
    'CJK_Compatibility_Ideographs.txt',
    'STPhrases.txt',
    'STPhrases_GeneratedFromRegionalPhrases.txt',
    'STCharacters.txt',
)
TW_DICTIONARY_FILENAMES = (
    'TWPhrases.txt',
    'TWVariantsPhrases.txt',
    'TWVariants.txt',
)
CACHE_FILENAMES = (
    'convert_table_words.txt',
    'convert_table_chars.txt',
    'convert_table_words_twp.txt',
    'convert_table_chars_twp.txt',
    'code_points_han.txt',
)
TONGYONG_URL = 'https://raw.githubusercontent.com/rime-aca/character_set/e7d009a8a185a83f62ad2c903565b8bb85719221/%E9%80%9A%E7%94%A8%E8%A6%8F%E7%AF%84%E6%BC%A2%E5%AD%97%E8%A1%A8.txt'

def iter_dictionary(filename):
    with Path(opencc_data.data_path(filename)).open(encoding='utf-8') as dictionary:
        for line in dictionary:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            yield line.split('\t', 1)

def iter_extra_conversions():
    with (HERE / 'extra_convert_table.txt').open(encoding='utf-8') as dictionary:
        for line in dictionary:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            yield line.split('\t', 1)

def cache_is_current():
    marker = CACHE_DIR / 'version.txt'
    try:
        if marker.read_text(encoding='utf-8').strip() != CACHE_VERSION:
            return False
    except FileNotFoundError:
        return False
    required_files = [CACHE_DIR / filename for filename in CACHE_FILENAMES]
    required_files.append(CACHE_DIR / '通用規範漢字表.txt')
    return all(filename.is_file() for filename in required_files)

def download_data():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    urlretrieve(TONGYONG_URL, CACHE_DIR / '通用規範漢字表.txt')

def write_table(filename, entries):
    entries = sorted(entries.items(), key=lambda item: (len(item[0]), item[0]), reverse=True)
    with (CACHE_DIR / filename).open('w', encoding='utf-8') as output:
        for key, value in entries:
            print(key, value, sep='\t', file=output)

def write_split_tables(word_filename, char_filename, entries):
    words = {key: value for key, value in entries.items() if len(key) > 1}
    characters = {key: value for key, value in entries.items() if len(key) == 1}
    write_table(word_filename, words)
    write_table(char_filename, characters)

def build_standard_entries():
    converter = OpenCC('s2t').convert
    keys = {key for filename in STANDARD_DICTIONARY_FILENAMES for key, _ in iter_dictionary(filename)}
    entries = {key: converter(key) for key in keys}
    entries.update(iter_extra_conversions())
    return entries

def build_convert_tables():
    standard_entries = build_standard_entries()
    t2twp = OpenCC(str(HERE / 't2twp.json')).convert
    t2s = OpenCC('t2s').convert
    twp_entries = {key: t2twp(value) for key, value in standard_entries.items()}
    # Preserve the original flat t2twp algorithm: recover Simplified keys from
    # the Taiwan dictionaries, then merge every mapping into one table.
    for filename in reversed(TW_DICTIONARY_FILENAMES):
        for key, candidates in iter_dictionary(filename):
            twp_entries[t2s(key)] = candidates.split(' ')[0]
    write_split_tables('convert_table_words.txt', 'convert_table_chars.txt', standard_entries)
    write_split_tables('convert_table_words_twp.txt', 'convert_table_chars_twp.txt', twp_entries)

def build_codepoints():
    codepoints = set()
    with (CACHE_DIR / '通用規範漢字表.txt').open(encoding='utf-8') as table:
        for line in table:
            if line and not line.startswith('#'):
                codepoints.add(ord(line[0]))
    for key, candidates in chain.from_iterable(iter_dictionary(filename) for filename in OPENCC_DATA_FILENAMES):
        codepoints.update(ord(character) for character in key)
        codepoints.update(ord(character) for candidate in candidates.split(' ') for character in candidate)
    codepoints.update(ord(character) for character in '妳攞噉㗎冚喺冇哋啲嘢啱佢嘅咁嚟屌咗撚噏瞓𡃁嘥掹孭氹詏噃𨳍掟埞曱甴𥄫𨳊嚿閪冧嬲卌嗻𧨾')
    with (CACHE_DIR / 'code_points_han.txt').open('w', encoding='utf-8') as output:
        for codepoint in sorted(codepoints):
            if codepoint > 128:
                print(codepoint, file=output)

def prepare_data():
    installed_version = version('opencc-data')
    if installed_version != OPENCC_DATA_VERSION:
        raise RuntimeError(f'opencc-data {OPENCC_DATA_VERSION} is required, found {installed_version}')
    if cache_is_current():
        return
    download_data()
    build_convert_tables()
    build_codepoints()
    (CACHE_DIR / 'version.txt').write_text(CACHE_VERSION + '\n', encoding='utf-8')
