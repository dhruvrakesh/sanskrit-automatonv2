import os, pathlib, sys
src = pathlib.Path(os.path.expanduser('~/mnt/Sanksrit Automatons/sanskrit-automatonv2'))
dst = pathlib.Path(os.path.expanduser(sys.argv[1]))
ch = []; n = 0
for top in ('scripts', 'tests', 'docs', 'configs'):
    for p in (src / top).rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts: continue
        rel = p.relative_to(src); d = dst / rel
        try:
            b = p.read_bytes()
        except OSError:
            continue
        n += 1
        if not d.exists() or d.read_bytes() != b:
            d.parent.mkdir(parents=True, exist_ok=True); d.write_bytes(b); os.utime(d, (p.stat().st_atime, p.stat().st_mtime)); ch.append(str(rel))
for p in src.iterdir():
    if p.is_file() and p.suffix in ('.md', '.toml', '.txt', '.ps1'):
        d = dst / p.name; b = p.read_bytes()
        if not d.exists() or d.read_bytes() != b:
            d.write_bytes(b); ch.append(p.name)
print(n, 'files;', len(ch), 'refreshed'); print([c for c in ch if not c.startswith('docs/srangam')][:60])
