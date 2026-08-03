from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from OpenCCFontGenerator.font import build_cmap_rev, build_opencc_char_table, build_opencc_word_table, clean_empty_layout_tables, clean_unused_glyphs, get_font_style, remove_codepoints

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

class CleanEmptyLayoutTablesTests(TestCase):
    def test_removes_empty_subtables_lookups_features_and_references(self):
        obj = {
            'GSUB': {
                'languages': {'DFLT_DFLT': {'features': ['liga_keep', 'liga_drop', 'calt_drop']}},
                'features': {'liga_keep': ['lookup_liga_keep'], 'liga_drop': ['lookup_liga_drop'], 'calt_drop': ['lookup_calt_drop']},
                'lookups': {
                    'lookup_liga_keep': {'type': 'gsub_single', 'subtables': [{}, {'a': 'b'}]},
                    'lookup_liga_drop': {'type': 'gsub_ligature', 'subtables': [{'substitutions': []}]},
                    'lookup_calt_drop': {'type': 'gsub_chaining', 'subtables': [{'match': [['a']], 'apply': [{'at': 0, 'lookup': 'lookup_liga_drop'}], 'inputBegins': 0, 'inputEnds': 1}]},
                },
                'lookupOrder': ['lookup_liga_keep', 'lookup_liga_drop', 'lookup_calt_drop'],
            },
            'GPOS': {
                'languages': {'DFLT_DFLT': {'features': ['palt_keep', 'vkrn_drop']}},
                'features': {'palt_keep': ['lookup_palt_keep'], 'vkrn_drop': ['lookup_vkrn_drop']},
                'lookups': {
                    'lookup_palt_keep': {'type': 'gpos_single', 'subtables': [{}, {'a': {'xAdvance': 1}}]},
                    'lookup_vkrn_drop': {'type': 'gpos_pair', 'subtables': [{'first': {}, 'second': {'b': 1}, 'matrix': []}]},
                },
                'lookupOrder': ['lookup_palt_keep', 'lookup_vkrn_drop'],
            },
        }

        clean_empty_layout_tables(obj)

        self.assertEqual(obj['GSUB']['lookups']['lookup_liga_keep']['subtables'], [{'a': 'b'}])
        self.assertNotIn('lookup_liga_drop', obj['GSUB']['lookups'])
        self.assertNotIn('lookup_calt_drop', obj['GSUB']['lookups'])
        self.assertEqual(obj['GSUB']['features'], {'liga_keep': ['lookup_liga_keep']})
        self.assertEqual(obj['GSUB']['languages']['DFLT_DFLT']['features'], ['liga_keep'])
        self.assertEqual(obj['GSUB']['lookupOrder'], ['lookup_liga_keep'])
        self.assertEqual(obj['GPOS']['lookups']['lookup_palt_keep']['subtables'], [{'a': {'xAdvance': 1}}])
        self.assertNotIn('lookup_vkrn_drop', obj['GPOS']['lookups'])
        self.assertEqual(obj['GPOS']['features'], {'palt_keep': ['lookup_palt_keep']})
        self.assertEqual(obj['GPOS']['languages']['DFLT_DFLT']['features'], ['palt_keep'])
        self.assertEqual(obj['GPOS']['lookupOrder'], ['lookup_palt_keep'])

class GlyphReachabilityTests(TestCase):
    def test_preserves_transitive_substitutions_components_and_variation_sequences(self):
        cmap = {'65': 'base', '66': 'component', '67': 'multiple', '68': 'unused', '69': 'discarded_base'}
        obj = {
            'cmap': cmap,
            'cmap_rev': build_cmap_rev({'cmap': cmap}),
            'cmap_uvs': {'65 65024': 'variant', '69 65024': 'discarded_variant'},
            'glyph_order': ['.notdef', '.null', 'base', 'component', 'multiple', 'variant', 'unused', 'unused.alt', 'discarded_base', 'discarded_variant'],
            'glyf': {
                '.notdef': {},
                '.null': {},
                'base': {'references': [{'glyph': 'component'}]},
                'component': {},
                'multiple': {},
                'variant': {},
                'unused': {},
                'unused.alt': {},
                'discarded_base': {},
                'discarded_variant': {},
            },
            'GSUB': {
                'languages': {'DFLT_DFLT': {'features': ['ccmp', 'calt']}},
                'features': {'ccmp': ['lookup_multiple'], 'calt': ['lookup_chaining']},
                'lookups': {
                    'lookup_multiple': {'type': 'gsub_multiple', 'subtables': [{'base': ['multiple']}]},
                    'lookup_chaining': {'type': 'gsub_chaining', 'subtables': [{'match': [['base'], ['unused']], 'apply': [{'at': 1, 'lookup': 'lookup_single'}], 'inputBegins': 0, 'inputEnds': 2}]},
                    'lookup_single': {'type': 'gsub_single', 'subtables': [{'unused': 'unused.alt'}]},
                },
                'lookupOrder': ['lookup_multiple', 'lookup_chaining', 'lookup_single'],
            },
            'GPOS': {'languages': {}, 'features': {}, 'lookups': {}, 'lookupOrder': []},
        }

        remove_codepoints(obj, (66, 67, 68, 69))
        clean_unused_glyphs(obj)
        clean_empty_layout_tables(obj)

        self.assertEqual(set(obj['glyph_order']), {'.notdef', '.null', 'base', 'component', 'multiple', 'variant'})
        self.assertEqual(obj['cmap'], {'65': 'base'})
        self.assertEqual(obj['cmap_uvs'], {'65 65024': 'variant'})
        self.assertEqual(set(obj['GSUB']['lookups']), {'lookup_multiple'})
        self.assertEqual(obj['GSUB']['features'], {'ccmp': ['lookup_multiple']})
        self.assertEqual(obj['GSUB']['languages']['DFLT_DFLT']['features'], ['ccmp'])

class FontMetadataTests(TestCase):
    def test_prefers_typographic_subfamily_name(self):
        obj = {'name': [{'nameID': 2, 'nameString': 'Legacy'}, {'nameID': 17, 'nameString': 'Typographic'}]}

        self.assertEqual(get_font_style(obj), 'Typographic')

    def test_falls_back_to_legacy_subfamily_name(self):
        obj = {'name': [{'nameID': 2, 'nameString': 'Regular'}]}

        self.assertEqual(get_font_style(obj), 'Regular')
