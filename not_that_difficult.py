import csv
import sys
from pathlib import Path

import numpy as np


def shift(abc, shift_amount, text):
    return "".join(
        abc[(abc.index(i) + shift_amount) % len(abc)] if i in abc else i
        for i in text
    )


def load_frequencies(path):
    alphabet = []
    frequencies = []
    with path.open("r", encoding="utf-8") as file:
        for letter, percent in csv.reader(file):
            alphabet.append(letter.lower())
            frequencies.append(float(percent))
    return "".join(alphabet), np.array(frequencies)


def decipher(ciphertext, abc, frequencies):
    scores = []
    lower_text = ciphertext.lower()

    for offset in range(len(abc)):
        candidate = shift(abc, -offset, lower_text)
        counts = np.array([candidate.count(letter) for letter in abc], dtype=float)
        counts /= counts.sum() if counts.sum() else 1.0
        observed = counts * 100.0

        # Chi-squared statistics favor the offset whose letter frequencies best
        # match the known Norwegian frequencies.
        expected = frequencies
        safe_expected = np.where(expected > 0, expected, 1.0)
        score = np.sum((observed - expected) ** 2 / safe_expected)
        scores.append(score)

    offset = int(np.argmin(scores))
    return shift(abc, -offset, ciphertext), offset


def main():
    if len(sys.argv) != 2:
        print("Usage: python not_that_difficult.py <ciphertext.txt>", file=sys.stderr)
        return 1

    input_path = Path(sys.argv[1])
    try:
        ciphertext = input_path.read_text(encoding="utf-8")
        csv_path = input_path.parent / "vanligst.csv"
        if not csv_path.exists():
            csv_path = Path(__file__).resolve().parent / "vanligst.csv"
        abc, frequencies = load_frequencies(csv_path)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    plaintext, offset = decipher(ciphertext, abc, frequencies)
    print("Deciphered text:")
    print(plaintext)
    print(f"Offset: {offset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

