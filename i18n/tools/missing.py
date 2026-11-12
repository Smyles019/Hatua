"""List the English lines a file asks to translate that have no Swahili in i18n/sw.json.

Usage: python missing.py <file> [js|dart]
js:   lines in t('...') calls          dart: lines in tr('...') calls
Run it after adding text, so the Swahili file keeps up. Prints one line per gap.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def keys(src: str, fn: str) -> list[str]:
    found = []
    q = r"(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")"
    for m in re.finditer(rf"\b{fn}\(\s*{q}", src):
        found.append(m.group(1) if m.group(1) is not None else m.group(2))
    # tr(cond ? 'a' : 'b') and t(cond ? 'a' : 'b')
    for m in re.finditer(rf"\b{fn}\([^'\"()]*\?\s*{q}\s*:\s*{q}", src):
        found += [g for g in m.groups() if g is not None]
    out = []
    for k in found:
        k = k.replace("\\'", "'").replace('\\"', '"')
        if k not in out:
            out.append(k)
    return out


def main():
    path, kind = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "js")
    src = Path(path).read_text(encoding="utf-8")
    sw = {}
    for name, section in json.loads((ROOT / "i18n" / "sw.json").read_text(encoding="utf-8")).items():
        if not name.startswith("_"):
            sw.update(section)
    ks = keys(src, "t" if kind == "js" else "tr")
    gaps = [k for k in ks if k not in sw]
    for k in gaps:
        print(json.dumps(k, ensure_ascii=False))
    print(f"# {len(ks)} lines, {len(gaps)} without Swahili", file=sys.stderr)


if __name__ == "__main__":
    main()
