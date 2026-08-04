from collections import defaultdict
from datetime import date
from decimal import Decimal
from itertools import chain, groupby
import json
from os import path
import subprocess

from .data import DATA_DIR, verify_data

HERE = path.abspath(path.dirname(__file__))

# Define the max entries size in a subtable.
# We define a number that is small enough here, so that the entries will not exceed
# the size limit.
SUBTABLE_MAX_COUNT = 4000

# The following two functions are used to split a GSUB table into several subtables.

def grouper(iterable, n=SUBTABLE_MAX_COUNT):
    '''
    Split a list into chunks of size n.
    >>> list(grouper([1, 2, 3, 4, 5], n=2))
    [[1, 2], [3, 4], [5]]
    >>> list(grouper([1, 2, 3, 4, 5, 6], n=2))
    [[1, 2], [3, 4], [5, 6]]
    '''
    iterator = iter(iterable)
    while True:
        lst = []
        try:
            for _ in range(n):
                lst.append(next(iterator))
        except StopIteration:
            if lst:
                yield lst
            break
        yield lst

def grouper2(iterable, n=SUBTABLE_MAX_COUNT, key=None):
    '''
    Split a iterator into chunks of maximum size n by the given key.
    >>> list(grouper2(['AA', 'BBB', 'CCC', 'DDD', 'EE'], n=3, key=len))
    [['AA'], ['BBB', 'CCC', 'DDD'], ['EE']]
    >>> list(grouper2(['AA', 'BBB', 'CCC', 'DDD', 'EE'], n=2, key=len))
    [['AA'], ['BBB', 'CCC'], ['DDD'], ['EE']]
    '''
    for _, vx in groupby(iterable, key=key):
        for vs in grouper(vx, n):
            yield vs

# An opentype font can hold at most 65535 glyphs.
MAX_GLYPH_COUNT = 65535

# Here we are going to add a special key, cmap_rev, to the font object.
# This key is the reverse mapping of the cmap table and will be used in next steps.

def build_cmap_rev(obj):
    cmap_rev = defaultdict(list)
    for codepoint, glyph_name in obj['cmap'].items():
        cmap_rev[glyph_name].append(codepoint)
    return cmap_rev

def load_font(path, ttc_index=None):
    '''Load a font as a JSON object.'''
    ttc_index_args = () if ttc_index is None else ('--ttc-index', str(ttc_index))
    obj = json.loads(subprocess.check_output(('otfccdump', path, *ttc_index_args)))
    obj['cmap_rev'] = build_cmap_rev(obj)
    return obj

def save_font(obj, path):
    '''Save a font object to file.'''
    cmap_rev = obj.pop('cmap_rev')
    try:
        subprocess.run(('otfccbuild', '-o', path), input=json.dumps(obj), encoding='utf-8', check=True)
    finally:
        obj['cmap_rev'] = cmap_rev

def codepoint_to_glyph_name(obj, codepoint):
    '''Convert a codepoint to a glyph name in a font.'''
    return obj['cmap'][str(codepoint)]

def insert_empty_glyph(obj, name):
    '''Insert an empty glyph to a font with the given name.'''
    obj['glyf'][name] = {'advanceWidth': 0, 'advanceHeight': 1000, 'verticalOrigin': 880}
    obj['glyph_order'].append(name)

def get_glyph_count(obj):
    '''Get the total numbers of glyph in a font.'''
    return len(obj['glyph_order'])

def build_codepoints_han():
    '''Build a set of codepoints of Han characters to be included.'''
    with (DATA_DIR / 'code_points_han.txt').open() as f:
        s = set()
        for line in f:
            s.add(int(line))
        return s

def build_codepoints_font(obj):
    '''Build a set of all the codepoints in a font.'''
    return set(map(int, obj['cmap']))

def build_codepoints_non_han():
    '''Build a set of codepoints of the needed non-Han characters in the final font.'''
    return set(chain(
        range(0x0020, 0x00FF + 1),
        range(0x02B0, 0x02FF + 1),
        range(0x2002, 0x203B + 1),
        range(0x2E00, 0x2E7F + 1),
        range(0x2E80, 0x2EFF + 1),
        range(0x3000, 0x301C + 1),
        range(0x3100, 0x312F + 1),
        range(0x3190, 0x31BF + 1),
        range(0xFE10, 0xFE1F + 1),
        range(0xFE30, 0xFE4F + 1),
        range(0xFF01, 0xFF5E + 1),
        range(0xFF5F, 0xFF60 + 1),
        range(0xFF61, 0xFF64 + 1),
    ))

def build_opencc_char_table(codepoints_font, twp=False):
    entries = []
    twp_suffix = '_twp' if twp else ''

    with (DATA_DIR / f'convert_table_chars{twp_suffix}.txt').open(encoding='utf-8') as f:
        for line in f:
            k, v = line.rstrip('\n').split('\t')
            codepoint_k = ord(k)
            codepoint_v = ord(v)
            # Source and target glyphs must both exist in the input font.
            if codepoint_k in codepoints_font and codepoint_v in codepoints_font:
                entries.append((codepoint_k, codepoint_v))

    return entries

def build_opencc_word_table(codepoints_font, twp=False):
    entries = []
    twp_suffix = '_twp' if twp else ''

    with (DATA_DIR / f'convert_table_words{twp_suffix}.txt').open(encoding='utf-8') as f:
        for line in f:
            k, v = line.rstrip('\n').split('\t')
            codepoints_k = tuple(ord(c) for c in k)
            codepoints_v = tuple(ord(c) for c in v)
            # Every source and target glyph must exist in the input font.
            if all(codepoint in codepoints_font for codepoint in codepoints_k) and all(codepoint in codepoints_font for codepoint in codepoints_v):
                entries.append((codepoints_k, codepoints_v))

    # The entries are already Sorted from longest to shortest to force longest match
    return entries

def disassociate_codepoint_and_glyph_name(obj, codepoint, glyph_name):
    '''
    Remove a codepoint from the cmap table of a font object.

    Returns `True` if the codepoint is the only codepoint that is associated
    with the glyph. Otherwise returns `False`.
    '''
    # Remove glyph from cmap table
    del obj['cmap'][codepoint]

    is_only_item = obj['cmap_rev'][glyph_name] == [codepoint]

    # Remove glyph from cmap_rev
    if is_only_item:
        del obj['cmap_rev'][glyph_name]
    else:
        obj['cmap_rev'][glyph_name].remove(codepoint)

    return is_only_item

def remove_codepoint(obj, codepoint):
    '''Remove a codepoint from a font object.'''
    codepoint = str(codepoint)

    glyph_name = obj['cmap'].get(codepoint)
    if glyph_name:
        disassociate_codepoint_and_glyph_name(obj, codepoint, glyph_name)

    variation_sequence_prefix = f'{codepoint} '
    for variation_sequence in list(obj.get('cmap_uvs', {})):
        if variation_sequence.startswith(variation_sequence_prefix):
            del obj['cmap_uvs'][variation_sequence]

def remove_codepoints(obj, codepoints):
    '''Remove a sequence of codepoints from a font object.'''
    for codepoint in codepoints:
        remove_codepoint(obj, codepoint)

def remove_associated_codepoints_of_glyph(obj, glyph_name):
    '''Remove a glyph from the cmap table of a font object.'''
    # Remove glyph from cmap table
    for codepoint in obj['cmap_rev'][glyph_name]:
        del obj['cmap'][codepoint]

    # Remove glyph from cmap_rev
    del obj['cmap_rev'][glyph_name]

def remove_glyph(obj, glyph_name):
    '''Remove a glyph from all the tables except the cmap table of a font object.'''
    # Remove glyph from glyph_order table
    try:
        obj['glyph_order'].remove(glyph_name)
    except ValueError:
        pass

    # Remove glyph from glyf table
    del obj['glyf'][glyph_name]

    # Remove glyph from cmap variation sequences
    for variation_sequence, variation_glyph_name in list(obj.get('cmap_uvs', {}).items()):
        if variation_glyph_name == glyph_name:
            del obj['cmap_uvs'][variation_sequence]

    # Remove glyph from GSUB table
    for lookup in obj['GSUB']['lookups'].values():
        if lookup['type'] == 'gsub_single':  # {a: b}
            for subtable in lookup['subtables']:
                for k, v in list(subtable.items()):
                    if glyph_name == k or glyph_name == v:
                        del subtable[k]
        elif lookup['type'] in ('gsub_multiple', 'gsub_alternate'):  # {a: [b1, b2, ...]}
            for subtable in lookup['subtables']:
                for k, v in list(subtable.items()):
                    if glyph_name == k or glyph_name in v:
                        del subtable[k]
        elif lookup['type'] == 'gsub_ligature':  # {from: [a1, a2, ...], to: b}
            for subtable in lookup['subtables']:
                def predicate(item):
                    return glyph_name not in item['from'] and glyph_name != item['to']
                subtable['substitutions'][:] = filter(predicate, subtable['substitutions'])
        elif lookup['type'] == 'gsub_chaining':
            for subtable in lookup['subtables']:
                for coverage in subtable['match']:
                    coverage[:] = [candidate for candidate in coverage if candidate != glyph_name]
        else:
            raise NotImplementedError('Unknown GSUB lookup type')

    # Remove glyph from GPOS table
    for lookup in obj['GPOS']['lookups'].values():
        if lookup['type'] == 'gpos_single':  # {a: ...}
            for subtable in lookup['subtables']:
                subtable.pop(glyph_name, None)
        # {first: {a1: ..., a2: ...}, second: {b1: ..., b2: ...}, ...}
        elif lookup['type'] == 'gpos_pair':
            for subtable in lookup['subtables']:
                subtable['first'].pop(glyph_name, None)
                subtable['second'].pop(glyph_name, None)
        elif lookup['type'] == 'gpos_chaining':
            for subtable in lookup['subtables']:
                for coverage in subtable['match']:
                    coverage[:] = [candidate for candidate in coverage if candidate != glyph_name]
        else:
            raise NotImplementedError('Unknown GPOS lookup type')

def get_reachable_glyphs(obj):
    '''Get all the reachable glyphs of a font object.'''
    reachable_glyphs = {'.notdef', '.null', *obj['cmap'].values(), *obj.get('cmap_uvs', {}).values()}

    while True:
        previous_count = len(reachable_glyphs)
        for glyph_name in tuple(reachable_glyphs):
            glyph = obj['glyf'].get(glyph_name)
            if glyph:
                reachable_glyphs.update(reference['glyph'] for reference in glyph.get('references', ()))

        for lookup in obj['GSUB']['lookups'].values():
            if lookup['type'] == 'gsub_single':  # {a: b}
                for subtable in lookup['subtables']:
                    for k, v in subtable.items():
                        if k in reachable_glyphs:
                            reachable_glyphs.add(v)
            elif lookup['type'] in ('gsub_multiple', 'gsub_alternate'):  # {a: [b1, b2, ...]}
                for subtable in lookup['subtables']:
                    for k, vs in subtable.items():
                        if k in reachable_glyphs:
                            reachable_glyphs.update(vs)
            # {from: [a1, a2, ...], to: b}
            elif lookup['type'] == 'gsub_ligature':
                for subtable in lookup['subtables']:
                    for item in subtable['substitutions']:
                        if all(glyph_name in reachable_glyphs for glyph_name in item['from']):
                            reachable_glyphs.add(item['to'])
            elif lookup['type'] == 'gsub_chaining':
                pass
            else:
                raise NotImplementedError('Unknown GSUB lookup type')

        if len(reachable_glyphs) == previous_count:
            return reachable_glyphs

def clean_unused_glyphs(obj):
    reachable_glyphs = get_reachable_glyphs(obj)
    all_glyphs = set(obj['glyph_order'])
    for glyph_name in all_glyphs - reachable_glyphs:
        remove_associated_codepoints_of_glyph(obj, glyph_name)
        remove_glyph(obj, glyph_name)

def is_layout_subtable_empty(lookup, subtable):
    '''Return whether otfcc would discard a layout subtable as empty.'''
    if lookup['type'] == 'gsub_ligature':
        return not subtable['substitutions']
    if lookup['type'] in ('gsub_chaining', 'gpos_chaining'):
        return any(not coverage for coverage in subtable['match'])
    if lookup['type'] == 'gpos_pair':
        # An empty second class still represents the default class 0.
        return not subtable['first']
    return not subtable

def clean_empty_layout_tables(obj):
    '''Remove empty layout subtables, lookups, features, and references.'''
    for table_name in ('GSUB', 'GPOS'):
        table = obj[table_name]
        while True:
            lookup_names = set(table['lookups'])
            empty_lookup_names = set()
            for lookup_name, lookup in table['lookups'].items():
                retained_subtables = []
                for subtable in lookup['subtables']:
                    invalid_applications = False
                    if lookup['type'] in ('gsub_chaining', 'gpos_chaining') and subtable['apply']:
                        subtable['apply'][:] = [application for application in subtable['apply'] if application['lookup'] in lookup_names]
                        invalid_applications = not subtable['apply']
                    if not invalid_applications and not is_layout_subtable_empty(lookup, subtable):
                        retained_subtables.append(subtable)
                lookup['subtables'][:] = retained_subtables
                if not lookup['subtables']:
                    empty_lookup_names.add(lookup_name)

            if not empty_lookup_names:
                break
            for lookup_name in empty_lookup_names:
                del table['lookups'][lookup_name]

        lookup_names = set(table['lookups'])
        table['lookupOrder'][:] = [lookup_name for lookup_name in table['lookupOrder'] if lookup_name in lookup_names]
        for lookup_names in table['features'].values():
            lookup_names[:] = [lookup_name for lookup_name in lookup_names if lookup_name in table['lookups']]

        empty_feature_names = {feature_name for feature_name, lookup_names in table['features'].items() if not lookup_names}
        for feature_name in empty_feature_names:
            del table['features'][feature_name]
        for language in table['languages'].values():
            language['features'][:] = [feature_name for feature_name in language['features'] if feature_name not in empty_feature_names]

def insert_empty_feature(obj, feature_name):
    for table in obj['GSUB']['languages'].values():
        table['features'].append(feature_name)
    obj['GSUB']['features'][feature_name] = []

def create_word2pseu_table(obj, feature_name, conversions):
    def conversion_item_len(conversion_item): return len(conversion_item[0])
    subtables = [
        {'substitutions': [{'from': glyph_names_k, 'to': pseudo_glyph_name} for glyph_names_k, pseudo_glyph_name in subtable]}
        for subtable in grouper2(conversions, key=conversion_item_len)
    ]  # {from: [a1, a2, ...], to: b}
    obj['GSUB']['features'][feature_name].append('word2pseu')
    obj['GSUB']['lookups']['word2pseu'] = {
        'type': 'gsub_ligature',
        'flags': {},
        'subtables': subtables
    }
    obj['GSUB']['lookupOrder'].append('word2pseu')

def create_char2char_table(obj, feature_name, conversions):
    subtables = [{k: v for k, v in subtable} for subtable in grouper(conversions)]
    obj['GSUB']['features'][feature_name].append('char2char')
    obj['GSUB']['lookups']['char2char'] = {
        'type': 'gsub_single',
        'flags': {},
        'subtables': subtables
    }
    obj['GSUB']['lookupOrder'].append('char2char')

def create_pseu2word_table(obj, feature_name, conversions):
    def conversion_item_len(conversion_item): return len(conversion_item[1])
    subtables = [{k: v for k, v in subtable} for subtable in grouper2(conversions, key=conversion_item_len)]
    obj['GSUB']['features'][feature_name].append('pseu2word')
    obj['GSUB']['lookups']['pseu2word'] = {
        'type': 'gsub_multiple',
        'flags': {},
        'subtables': subtables
    }
    obj['GSUB']['lookupOrder'].append('pseu2word')

def build_name_header(name_header_file, style, version, date):
    with open(name_header_file) as f:
        name_header = json.load(f)

    for item in name_header:
        item['nameString'] = item['nameString'].replace('<Typographic Subfamily Name>', style).replace('<Version>', version).replace('<Date>', date)

    return name_header

def get_font_style(obj):
    '''Get the typographic or legacy subfamily name of a font.'''
    for name_id in (17, 2):
        for item in obj['name']:
            if item['nameID'] == name_id:
                return item['nameString']
    raise ValueError('The font has no subfamily name')

def modify_metadata(obj, name_header_file, font_version: Decimal):
    style = get_font_style(obj)
    today = date.today().strftime('%b %d, %Y')

    name_header = build_name_header(name_header_file, style, str(font_version), today)

    obj['head']['fontRevision'] = float(font_version)
    obj['name'] = name_header

def build_font(input_file, output_file, name_header_file, font_version, ttc_index=None, twp=False):
    verify_data()
    font = load_font(input_file, ttc_index=ttc_index)

    # Determine the final Unicode range by the original font and OpenCC convert tables

    codepoints_font = build_codepoints_font(font)
    entries_char = build_opencc_char_table(codepoints_font, twp=twp)
    entries_word = build_opencc_word_table(codepoints_font, twp=twp)

    codepoints_final = (build_codepoints_non_han() | build_codepoints_han()) & codepoints_font

    remove_codepoints(font, codepoints_font - codepoints_final)
    clean_unused_glyphs(font)

    # Build glyph substitution tables and insert into font

    available_glyph_count = MAX_GLYPH_COUNT - get_glyph_count(font)
    assert available_glyph_count >= len(entries_word)

    word2pseu_table = []
    char2char_table = []
    pseu2word_table = []

    for index, (codepoints_k, codepoints_v) in enumerate(entries_word):
        pseudo_glyph_name = 'pseu%X' % index
        glyph_names_k = [codepoint_to_glyph_name(font, codepoint) for codepoint in codepoints_k]
        glyph_names_v = [codepoint_to_glyph_name(font, codepoint) for codepoint in codepoints_v]
        insert_empty_glyph(font, pseudo_glyph_name)
        word2pseu_table.append((glyph_names_k, pseudo_glyph_name))
        pseu2word_table.append((pseudo_glyph_name, glyph_names_v))

    for codepoint_k, codepoint_v in entries_char:
        glyph_name_k = codepoint_to_glyph_name(font, codepoint_k)
        glyph_name_v = codepoint_to_glyph_name(font, codepoint_v)
        char2char_table.append((glyph_name_k, glyph_name_v))

    feature_name = 'rlig_s2t'
    insert_empty_feature(font, feature_name)
    create_word2pseu_table(font, feature_name, word2pseu_table)
    create_char2char_table(font, feature_name, char2char_table)
    create_pseu2word_table(font, feature_name, pseu2word_table)
    clean_empty_layout_tables(font)

    # Complete GBK retention would exceed the OpenType glyph limit, so advertise code page 936 while retaining the original GB2312 repertoire.
    font['OS_2']['ulCodePageRange1']['gbk'] = True
    modify_metadata(font, name_header_file, font_version)
    save_font(font, output_file)
