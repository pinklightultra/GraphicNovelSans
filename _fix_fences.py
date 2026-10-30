import pathlib

files = [
    "README.md",
    "docs/installation.md",
    "docs/quickstart.md",
    "docs/cli-guide.md",
    "docs/contributing.md",
    "docs/api/core.md",
    "docs/api/index.md",
]

FENCE = chr(96) * 3  # three backticks

def guess_lang(block):
    b = block.strip()
    if b.startswith("from ") or b.startswith("import ") or "ComicFont(" in b:
        return "python"
    if b.startswith(("pip ", "git ", "cd ", "graphicnovelsans")):
        return "bash"
    if ".ttf" in b or ".woff2" in b:
        return "text"
    return "text"

for f in files:
    p = pathlib.Path(f)
    lines = p.read_text().split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("    ") and line.strip():
            block = []
            while i < len(lines):
                cur = lines[i]
                if cur.startswith("    ") and cur.strip():
                    block.append(cur[4:])
                    i += 1
                elif cur.strip() == "":
                    j = i + 1
                    if j < len(lines) and lines[j].startswith("    ") and lines[j].strip():
                        block.append("")
                        i += 1
                    else:
                        break
                else:
                    break
            lang = guess_lang("\n".join(block))
            out.append(FENCE + lang)
            out.extend(block)
            out.append(FENCE)
        else:
            out.append(line)
            i += 1
    p.write_text("\n".join(out))
    print("processed " + f)