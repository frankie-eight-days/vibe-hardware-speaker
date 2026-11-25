#!/bin/sh
# Rebuild the design write-up: regenerate the pandoc/BOM appendices, then LuaLaTeX.
# Output: docs/build/design_doc.pdf   (aux files in docs/build/aux)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
export PATH=/Library/TeX/texbin:/opt/homebrew/bin:$PATH
cd "$HERE"
python3 convert_sources.py
mkdir -p ../build/aux
latexmk -lualatex -interaction=nonstopmode -halt-on-error -file-line-error \
  -outdir=../build/aux -jobname=design_doc main.tex
cp ../build/aux/design_doc.pdf ../build/design_doc.pdf
echo "Wrote $(cd ../build && pwd)/design_doc.pdf"
