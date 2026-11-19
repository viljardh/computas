#!/usr/bin/env python3
"""Decode text encrypted with a Caesar cipher using the Norwegian alphabet."""

import argparse


ALPHABET = "abcdefghijklmnopqrstuvwxyzæøå "


def decode(text: str, shift: int) -> str:
	"""Decode *text* by shifting alphabet characters backwards."""
	result = []
	for character in text:
		try:
			index = ALPHABET.index(character)
		except ValueError:
			result.append(character)
		else:
			result.append(ALPHABET[(index - shift) % len(ALPHABET)])
	return "".join(result)


def encode(text: str, shift: int) -> str:
	"""Encode *text* by shifting alphabet characters forwards."""
	return decode(text, -shift)


def main() -> None:
	parser = argparse.ArgumentParser(description="Decode a Norwegian Caesar cipher.")
	parser.add_argument("shift", type=int, help="Caesar cipher shift")
	parser.add_argument("file", help="file containing the encoded text")
	mode = parser.add_mutually_exclusive_group(required=True)
	mode.add_argument("-d", "--decode", action="store_true", help="decode the file")
	mode.add_argument("-e", "--encode", action="store_true", help="encode the file")
	args = parser.parse_args()

	with open(args.file, "r", encoding="utf-8") as input_file:
		text = input_file.read()
	print(encode(text, args.shift) if args.encode else decode(text, args.shift), end="")


if __name__ == "__main__":
	main()
