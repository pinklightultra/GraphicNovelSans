"""Score a blind transcription of the test sheet against the answer key.

Character error rate is the headline number, but the useful output is which
character the reader saw instead: a font with a 5% CER concentrated in one
confusable pair is a different problem from one with 5% spread everywhere.
"""
import json, os, sys
from collections import Counter

import paths as P


def edits(a, b):
    """Levenshtein distance plus the substitution/insert/delete pairs."""
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
    ops, i, j = [], n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            if a[i - 1] != b[j - 1]:
                ops.append((a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            ops.append((a[i - 1], ""))
            i -= 1
        else:
            ops.append(("", b[j - 1]))
            j -= 1
    return d[n][m], ops


def score(key="blindtest_key.json", read=None):
    truth = P.load(P.read(key))
    got = P.load(P.read(read))
    tot_c = tot_e = tot_w = tot_we = 0
    conf = Counter()
    rows = []
    for k in sorted(truth):
        t, g = truth[k], got.get(k, "")
        dist, ops = edits(t, g)
        conf.update(ops)
        tw, gw = t.split(), g.split()
        wd, _ = edits(tw, gw)
        tot_c += len(t)
        tot_e += dist
        tot_w += len(tw)
        tot_we += wd
        rows.append((k, len(t), dist, dist / len(t), wd, len(tw)))
    print(f"{'line':5} {'chars':>5} {'errs':>5} {'CER':>7}  {'word errs':>9}")
    for k, n, e, cer, wd, nw in rows:
        print(f"{k:5} {n:5} {e:5} {cer:7.1%}  {wd:>4}/{nw:<4}")
    print(f"\noverall CER {tot_e/tot_c:.2%} ({tot_e}/{tot_c} characters)")
    print(f"overall WER {tot_we/tot_w:.2%} ({tot_we}/{tot_w} words)")
    if conf:
        print("\nmost common confusions (expected -> read, '' = dropped/added):")
        for (a, b), n in conf.most_common(12):
            print(f"  {a or '_'!r:5} -> {b or '_'!r:5} x{n}")
    return tot_e / tot_c


if __name__ == "__main__":
    score(read=sys.argv[1] if len(sys.argv) > 1 else "blindtest_read.json")
