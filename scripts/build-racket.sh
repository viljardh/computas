#!/usr/bin/env bash
# Bygger Racket-programmet Netlify-funksjonen kjører, til netlify/racket/.
# Mappen er frittstående (ca. 45 MB, mest Racket selv) og ligger ikke i git.
# Trenger raco (Racket). Kjøres lokalt og i GitHub Actions før deploy.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf netlify/racket build
mkdir build
raco exe -o build/caesar-api netlify/caesar-api.rkt
raco distribute netlify/racket build/caesar-api
rm -rf build

echo "Bygget netlify/racket ($(du -sh netlify/racket | cut -f1))"
