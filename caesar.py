import sys
abc = "abcdefghijklmnopqrstuvwxyzæøå "
print("".join(abc[(abc.index(i) + int(sys.argv[2])) % len(abc)] if i in abc else i for i in sys.argv[1]))