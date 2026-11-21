#!/usr/bin/env bash
# Netlify-funksjoner kjører med glibc 2.34. Et Racket-program bygget mot 2.35 (Ubuntus pakke)
# gir "version `GLIBC_2.35' not found" der. Dette skriptet feiler hvis noe i netlify/racket
# trenger en nyere glibc, så vi finner det under bygging og ikke først etter deploy.
# Bruk: scripts/check-glibc.sh [grense]    (standard 2.34)
set -euo pipefail
cd "$(dirname "$0")/.."
limit="${1:-2.34}"

found=""
while IFS= read -r -d '' f; do
    # bare kjørbare filer og biblioteker (ELF) har glibc-krav
    [ "$(head -c4 "$f" | od -An -tx1 | tr -d ' ')" = "7f454c46" ] || continue
    v=$(objdump -T "$f" 2>/dev/null | grep -o 'GLIBC_[0-9][0-9.]*' | sed 's/^GLIBC_//' | sort -V | tail -1 || true)
    [ -n "$v" ] || continue
    printf '  glibc %-5s %s\n' "$v" "$f"
    found+="$v $f"$'\n'
done < <(find netlify/racket -type f -print0)

[ -n "$found" ] || { echo "Fant ingen kjørbare filer i netlify/racket. Har du bygget?"; exit 1; }
worst=$(printf '%s' "$found" | sort -V | tail -1)
worst_v=${worst%% *}
echo "Høyeste krav: glibc $worst_v (Netlify har $limit)"
if [ "$(printf '%s\n%s\n' "$worst_v" "$limit" | sort -V | tail -1)" != "$limit" ]; then
    echo "FEIL: ${worst#* } trenger glibc $worst_v, men Netlify-funksjoner har $limit." >&2
    exit 1
fi
echo "OK"
