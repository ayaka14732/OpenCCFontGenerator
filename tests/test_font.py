from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from OpenCCFontGenerator.font import build_opencc_char_table, build_opencc_word_table

class BuildOpenCCTableTests(TestCase):
    def test_char_table_requires_source_and_target_glyphs(self):
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / 'convert_table_chars.txt').write_text('甲\t乙\n丙\t乙\n甲\t丁\n戊\t己\n', encoding='utf-8')
            with patch('OpenCCFontGenerator.font.DATA_DIR', data_dir):
                entries = build_opencc_char_table({ord('甲'), ord('乙')})

        self.assertEqual(entries, [(ord('甲'), ord('乙'))])

    def test_word_table_requires_every_source_and_target_glyph(self):
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / 'convert_table_words.txt').write_text('甲乙\t丙丁\n甲戊\t丙丁\n甲乙\t丙己\n庚辛\t壬癸\n', encoding='utf-8')
            with patch('OpenCCFontGenerator.font.DATA_DIR', data_dir):
                entries = build_opencc_word_table({ord(character) for character in '甲乙丙丁'})

        self.assertEqual(entries, [((ord('甲'), ord('乙')), (ord('丙'), ord('丁')))])
