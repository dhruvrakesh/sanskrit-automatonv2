import sys, requests
from urllib.parse import urlencode

if len(sys.argv) < 4:
    print("Usage: python export_via_api.py DOC PAGE_FROM PAGE_TO [TITLE]")
    sys.exit(2)

params = dict(
    doc=sys.argv[1],
    page_from=int(sys.argv[2]),
    page_to=int(sys.argv[3]),
    include_san=True, include_en=True,
    side_by_side=True, number_pages=True,
    title=sys.argv[4] if len(sys.argv) > 4 else sys.argv[1],
)
url = "http://127.0.0.1:8000/api/export/html?" + urlencode(params)
r = requests.get(url, timeout=120)
r.raise_for_status()
out = f"{params['doc']}_{params['page_from']}-{params['page_to']}.html"
with open(out, "wb") as f: f.write(r.content)
print("Wrote", out)
