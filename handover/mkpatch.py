"""edits(old, new): anchored (old_snippet, new_snippet) pairs, each old_snippet unique in old, applied in order."""
import difflib


def edits(o: str, n: str, ctx: int = 2):
    a, b = o.split("\n"), n.split("\n")
    ops = [op for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op[0] != "equal"]
    hunks = []
    for tag, i1, i2, j1, j2 in ops:
        c = ctx
        while True:
            s, e = max(0, i1 - c), min(len(a), i2 + c)
            old = "\n".join(a[s:e])
            if (o.count(old) == 1 and old.strip()) or (s == 0 and e == len(a)):
                break
            c += 1
        hunks.append([s, e, j1 - (i1 - s), j2 + (e - i2)])
    merged = []
    for h in hunks:
        if merged and h[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], h[1]); merged[-1][3] = max(merged[-1][3], h[3])
        else:
            merged.append(h)
    out = []
    for s, e, js, je in merged:
        old = "\n".join(a[s:e]); new = "\n".join(b[js:je])
        assert o.count(old) == 1, ("anchor not unique", old[:80])
        out.append((old, new))
    # replay check
    t = o
    for old, new in out:
        assert t.count(old) == 1
        t = t.replace(old, new)
    assert t == n, "replay differs"
    return out
