from importlib.metadata import version
from itertools import chain
from pathlib import Path
from urllib.request import urlretrieve

import opencc_data
from opencc import OpenCC

HERE = Path(__file__).resolve().parent
PACKAGE_DIR = HERE / 'src' / 'OpenCCFontGenerator'
OPENCC_DATA_VERSION = '1.4.1'
DATA_SCHEMA_VERSION = 5
DATA_VERSION = f'opencc-data-{OPENCC_DATA_VERSION}-schema-{DATA_SCHEMA_VERSION}'
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
GENERATED_FILENAMES = (
    'convert_table_words.txt',
    'convert_table_chars.txt',
    'convert_table_words_twp.txt',
    'convert_table_chars_twp.txt',
    'code_points_han.txt',
    'version.txt',
    '通用規範漢字表.txt',
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
    with (PACKAGE_DIR / 'extra_convert_table.txt').open(encoding='utf-8') as dictionary:
        for line in dictionary:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            yield line.split('\t', 1)

def write_table(output_dir, filename, entries):
    entries = sorted(entries.items(), key=lambda item: (len(item[0]), item[0]), reverse=True)
    with (output_dir / filename).open('w', encoding='utf-8') as output:
        for key, value in entries:
            print(key, value, sep='\t', file=output)

def write_split_tables(output_dir, word_filename, char_filename, entries):
    words = {key: value for key, value in entries.items() if len(key) > 1}
    characters = {key: value for key, value in entries.items() if len(key) == 1}
    write_table(output_dir, word_filename, words)
    write_table(output_dir, char_filename, characters)

def build_standard_entries():
    converter = OpenCC('s2t').convert
    keys = {key for filename in STANDARD_DICTIONARY_FILENAMES for key, _ in iter_dictionary(filename)}
    entries = {key: converter(key) for key in keys}
    entries.update(iter_extra_conversions())
    return entries

def build_convert_tables(output_dir):
    standard_entries = build_standard_entries()
    t2twp = OpenCC(str(PACKAGE_DIR / 't2twp.json')).convert
    t2s = OpenCC('t2s').convert
    twp_entries = {key: t2twp(value) for key, value in standard_entries.items()}
    # Preserve the original flat t2twp algorithm: recover Simplified keys from
    # the Taiwan dictionaries, then merge every mapping into one table.
    for filename in reversed(TW_DICTIONARY_FILENAMES):
        for key, candidates in iter_dictionary(filename):
            twp_entries[t2s(key)] = candidates.split(' ')[0]
    write_split_tables(output_dir, 'convert_table_words.txt', 'convert_table_chars.txt', standard_entries)
    write_split_tables(output_dir, 'convert_table_words_twp.txt', 'convert_table_chars_twp.txt', twp_entries)

def build_codepoints(output_dir):
    codepoints = set()
    with (output_dir / '通用規範漢字表.txt').open(encoding='utf-8') as table:
        for line in table:
            if line and not line.startswith('#'):
                codepoints.add(ord(line[0]))
    for key, candidates in chain.from_iterable(iter_dictionary(filename) for filename in OPENCC_DATA_FILENAMES):
        codepoints.update(ord(character) for character in key)
        codepoints.update(ord(character) for candidate in candidates.split(' ') for character in candidate)
    codepoints.update(ord(character) for character in '妳攞噉㗎冚喺冇哋啲嘢啱佢嘅咁嚟屌咗撚噏瞓𡃁嘥掹孭氹詏噃𨳍掟埞曱甴𥄫𨳊嚿閪冧嬲卌嗻𧨾')
    with (output_dir / 'code_points_han.txt').open('w', encoding='utf-8') as output:
        for codepoint in sorted(codepoints):
            if codepoint > 128:
                print(codepoint, file=output)

def build_data(output_dir):
    installed_version = version('opencc-data')
    if installed_version != OPENCC_DATA_VERSION:
        raise RuntimeError(f'opencc-data {OPENCC_DATA_VERSION} is required, found {installed_version}')
    output_dir.mkdir(parents=True, exist_ok=True)
    urlretrieve(TONGYONG_URL, output_dir / '通用規範漢字表.txt')
    build_convert_tables(output_dir)
    build_codepoints(output_dir)
    (output_dir / 'version.txt').write_text(DATA_VERSION + '\n', encoding='utf-8')
