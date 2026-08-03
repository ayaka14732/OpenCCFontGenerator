# OpenCC Font Generator

OpenCC Font Generator turns OpenCC's forward maximum-matching conversions into OpenType GSUB substitutions. Words are first replaced by pseudo-glyphs, characters are then converted, and the pseudo-glyphs are finally expanded to the converted words.

The generator currently uses [`nk2028/opencc-data` 1.4.1](https://github.com/nk2028/opencc-data/releases/tag/1.4.1) through the matching [`opencc-py` 1.4.1](https://pypi.org/project/opencc-py/1.4.1/) implementation and requires Python 3.14 or newer. Generated conversion tables are cached on first use under `$XDG_CACHE_HOME/OpenCCFontGenerator` or `~/.cache/OpenCCFontGenerator`; set `OPENCCFONTGENERATOR_CACHE_DIR` to override the location.

Taiwan conversion preserves the project's original flat `t2twp` algorithm. Standard Simplified-to-Traditional results are converted through `t2twp`; Taiwan dictionary keys are also recovered through `t2s`; then every phrase is merged into one longest-match GSUB lookup. This covers fully Simplified inputs such as `卷积` → `摺積` and `吃茶小铺` → `喫茶小舖`.

## Usage

Install `otfccdump` and `otfccbuild`, then install this project and run:

```console
python -m OpenCCFontGenerator --input-file source.ttc --ttc-index 0 --output-file output.ttf --name-header-file name.json --font-version 2.100
```

Add `--twp` to use Taiwan phrases and variants.
