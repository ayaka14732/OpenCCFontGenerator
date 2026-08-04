from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / 'generated'
DATA_VERSION = 'opencc-data-1.4.1-schema-6'
DATA_FILENAMES = (
    'convert_table_words.txt',
    'convert_table_chars.txt',
    'convert_table_words_twp.txt',
    'convert_table_chars_twp.txt',
    'code_points_han.txt',
)

def verify_data():
    marker = DATA_DIR / 'version.txt'
    try:
        bundled_version = marker.read_text(encoding='utf-8').strip()
    except FileNotFoundError:
        raise RuntimeError('bundled OpenCC conversion data is missing') from None
    if bundled_version != DATA_VERSION:
        raise RuntimeError(f'bundled OpenCC conversion data {DATA_VERSION} is required, found {bundled_version}')
    missing_files = [filename for filename in DATA_FILENAMES if not (DATA_DIR / filename).is_file()]
    if missing_files:
        raise RuntimeError(f'bundled OpenCC conversion data is incomplete: {", ".join(missing_files)}')
