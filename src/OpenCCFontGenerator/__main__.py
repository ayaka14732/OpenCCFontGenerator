import argparse
from decimal import Decimal, InvalidOperation

from .font import build_font

def parse_font_version(value):
    try:
        version = Decimal(value)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError('font version must be a decimal number') from error
    if not version.is_finite() or version <= 0:
        raise argparse.ArgumentTypeError('font version must be a positive finite decimal number')
    return version

def main():
    parser = argparse.ArgumentParser(description='OpenCC Font Generator')

    parser.add_argument('-i', '--input-file', type=str, required=True, help='path to the source font file')
    parser.add_argument('-o', '--output-file', type=str, required=True, help='path to the generated font file')
    parser.add_argument('-n', '--name-header-file', type=str, required=True, help='path to the name header configuration file (in JSON format)')
    parser.add_argument('--ttc-index', type=int, help='the font index in a TrueType Collection (TTC) file')
    parser.add_argument('--font-version', type=parse_font_version, required=True, help='the version of the generated font file')
    parser.add_argument('--twp', action=argparse.BooleanOptionalAction, default=False, help='whether to convert with Taiwanese phrases')

    args = parser.parse_args()

    build_font(args.input_file, args.output_file, args.name_header_file, args.font_version, ttc_index=args.ttc_index, twp=args.twp)

if __name__ == '__main__':
    main()
