# OpenCC Font Generator

OpenCC Font Generator creates OpenType fonts that display Simplified Chinese text as Traditional Chinese, including context-sensitive conversions where one Simplified character may have several Traditional forms. It can also generate a Taiwan variant with Taiwanese phrases and character forms.

## Usage

Install Python 3.14 or later and make sure `otfccdump` and `otfccbuild` are available in `PATH`. Then install OpenCC Font Generator:

```console
python -m pip install git+https://github.com/ayaka14732/OpenCCFontGenerator.git
```

Prepare a JSON file containing the output font's name records. The [Fan Wun Ming configuration](https://github.com/ayaka14732/FanWunMing/blob/main/config/name.json) can be used as an example.

Generate a font with:

```console
python -m OpenCCFontGenerator --input-file source.ttc --ttc-index 0 --output-file output.ttf --name-header-file name.json --font-version 2.100
```

Omit `--ttc-index` when the source is not a TrueType Collection. Add `--twp` to use Taiwanese phrases and variants.

## Design Principles

A conversion font changes how text is displayed without changing the underlying text. The design is described in [_Correctly Implement a Simplified-Chinese-To-Traditional-Chinese Font_](https://ayaka.shn.hk/s2tfont/hant/).
