import os, pathlib, shutil, sys
src = pathlib.Path(os.path.expanduser('~/mnt/srangam-42267')); dst = pathlib.Path(os.path.expanduser('~/work/srx'))
n = ch = 0; gone = 0
SKIP = {'node_modules', 'dist', '.git', 'dist_b2'}
for top in ('src', 'public', 'supabase', 'scripts', 'e2e', 'content'):
    s = src / top
    if not s.exists(): continue
    for p in s.rglob('*'):
        if not p.is_file() or any(x in SKIP for x in p.parts) or '.bak_' in p.name: continue
        rel = p.relative_to(src); d = dst / rel; n += 1
        b = p.read_bytes()
        if not d.exists() or d.read_bytes() != b:
            d.parent.mkdir(parents=True, exist_ok=True); d.write_bytes(b); ch += 1
    # files in dst not in src (under src/ only): remove so the copy equals main
    for p in list((dst / top).rglob('*')) if (dst / top).exists() else []:
        if p.is_file() and '.bak_' not in p.name and not (src / p.relative_to(dst)).exists() and top == 'src':
            p.unlink(); gone += 1
for f in ('package.json', 'package-lock.json', 'tsconfig.json', 'tsconfig.app.json', 'tsconfig.node.json', 'vite.config.ts', 'vitest.config.ts', 'index.html', 'tailwind.config.ts', 'postcss.config.js', 'eslint.config.js', 'components.json'):
    p = src / f
    if p.exists():
        b = p.read_bytes(); d = dst / f
        if not d.exists() or d.read_bytes() != b: d.write_bytes(b); ch += 1
print(n, 'files;', ch, 'refreshed;', gone, 'removed')
