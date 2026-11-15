import sys
for p in sys.argv[1:]:
    t = open(p, encoding="utf-8").read()
    out = "".join(c if ord(c) < 128 else ("\\u%04x" % ord(c) if ord(c) < 0x10000 else "\\U%08x" % ord(c)) for c in t)
    open(p, "w", encoding="ascii", newline="").write(out)
    print("asciified", p, sum(1 for c in t if ord(c) > 127))
