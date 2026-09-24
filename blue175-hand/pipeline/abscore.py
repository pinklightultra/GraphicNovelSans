"""Score a digit A/B sheet: per-arm CER, per-glyph accuracy, and what it was read as.

`score.py` pools confusions over a whole sheet, which is right when one font is
under test. Here several fonts share a sheet and the question is not "which sheet
read better" but "which pick for this one character". So each line is scored
against its own arm, and the per-character accuracy is reported per arm.

Per-glyph accuracy needs to know *which* truth character each read character
landed on, so this keeps the alignment itself rather than just the edit ops.

Round 1's arms cross two picks (`2` old/new by `5` old/new), so passing
`--cross` also pools the arms by each pick and reports it as a main effect.
Round 2 has one pick under test and the arm is the condition, so it does not.
"""
import json, os, sys
from collections import Counter, defaultdict

import paths as P
WATCH = "0123456789"        # characters worth a per-arm accuracy line
CROSS = {"2": {"A": "old", "C": "old", "B": "new", "D": "new"},
         "5": {"A": "old", "D": "old", "B": "new", "C": "new"}}


def align(a, b):
    """Levenshtein alignment as ordered (truth, read) pairs, '' for a gap."""
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    out, i, j = [], n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            out.append((a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            out.append((a[i - 1], ""))
            i -= 1
        else:
            out.append(("", b[j - 1]))
            j -= 1
    return d[n][m], out[::-1]


def load(reads, key):
    truth = P.load(P.read(key))
    per_arm = defaultdict(lambda: [0, 0])          # arm -> [errs, chars]
    glyph = defaultdict(lambda: [0, 0])            # (arm, ch) -> [hits, seen]
    conf = defaultdict(Counter)                    # arm -> Counter((truth, read))
    missing = []
    for r in reads:
        got = P.load(P.read(r))
        for line, meta in sorted(truth.items()):
            arm, t = meta["arm"], meta["text"]
            g = got.get(line)
            if g is None:
                missing.append((r, line))
                g = ""
            dist, pairs = align(t, g)
            per_arm[arm][0] += dist
            per_arm[arm][1] += len(t)
            for tc, gc in pairs:
                if tc:
                    glyph[(arm, tc)][1] += 1
                    glyph[(arm, tc)][0] += (tc == gc)
                if tc != gc:
                    conf[arm][(tc, gc)] += 1
    return truth, per_arm, glyph, conf, missing


def read_as(conf, arms, ch, n=5):
    c = Counter()
    for a in arms:
        for (tc, gc), k in conf[a].items():
            if tc == ch:
                c[gc or "_dropped_"] += k
    return ", ".join(f"{g!r} x{k}" for g, k in c.most_common(n)) or "nothing"


def report(reads, key, cross=False):
    truth, per_arm, glyph, conf, missing = load(reads, key)
    if missing:
        print("MISSING LINES:", missing)
    arms = sorted(per_arm)
    print(f"{len(reads)} readers, {len(truth)//len(arms)} lines per arm\n")
    print(f"{'arm':5} {'CER':>8}   " + "  ".join(f"{c:>7}" for c in WATCH))
    for a in arms:
        e, n = per_arm[a]
        cells = []
        for c in WATCH:
            h, s = glyph[(a, c)]
            cells.append(f"{h:2}/{s:<2} " if s else "   -   ")
        print(f"{a:5} {e/n:7.2%}   " + " ".join(cells))

    print("\nwhat each arm's digits were read as:")
    for a in arms:
        for c in WATCH:
            h, s = glyph[(a, c)]
            if s and h < s:
                print(f"  {a} {c!r}: {h}/{s} correct; {read_as(conf, [a], c)}")

    if cross:
        print("\nmain effects (arms pooled by the pick under test):")
        for ch, groups in CROSS.items():
            line = []
            for cond in ("old", "new"):
                ga = [a for a, c in groups.items() if c == cond and a in per_arm]
                h = sum(glyph[(a, ch)][0] for a in ga)
                s = sum(glyph[(a, ch)][1] for a in ga)
                line.append((cond, h, s, h / s if s else 0.0))
            best = max(line, key=lambda r: r[3])[0]
            desc = "   ".join(f"{c} {h:2}/{s:<3} {r:5.0%}" for c, h, s, r in line)
            print(f"  {ch!r}  {desc}   -> {best}")

    print("\nconfusions on characters not under test (pooled, sanity check):")
    c = Counter()
    for a in arms:
        for (tc, gc), n in conf[a].items():
            if tc not in "25":
                c[(tc or "_", gc or "_")] += n
    for (tc, gc), n in c.most_common(10):
        print(f"  {tc!r:5} -> {gc!r:5} x{n}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--cross"]
    cross = "--cross" in sys.argv
    rnd = args[0] if args and args[0].isdigit() else "1"
    reads = args[1:] if args and args[0].isdigit() else args
    suffix = "" if rnd == "1" else rnd
    key = f"abtest{suffix}_key.json"
    reads = reads or [f"ab{suffix}_read{i}.json" for i in (1, 2, 3)]
    report(reads, key, cross=cross or rnd == "1")
