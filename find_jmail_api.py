import urllib.request, gzip, re, json

HEADERS = {
    'accept': 'text/html,*/*',
    'cookie': 'jmail_anim_suppress=1; jsuite_user_id=anon_2c430467-69f5-4a69-9ad7-e899d5e8dd43',
    'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1 Edg/145.0.0.0',
}
JS_HEADERS = {**HEADERS, 'referer': 'https://jmail.world/person'}

req = urllib.request.Request('https://jmail.world/person', headers=HEADERS)
with urllib.request.urlopen(req, timeout=20) as r:
    raw = r.read()
    if 'gzip' in r.info().get('Content-Encoding',''):
        raw = gzip.decompress(raw)
    html = raw.decode('utf-8', errors='replace')

chunks = re.findall(r'src="(/_next/static/chunks/[^"]+\.js[^"]*?)"', html)
print(f'Found {len(chunks)} JS chunks - downloading all...\n')

all_routes = set()
for chunk_path in chunks:
    url = 'https://jmail.world' + chunk_path.split('?')[0]
    try:
        req2 = urllib.request.Request(url, headers=JS_HEADERS)
        with urllib.request.urlopen(req2, timeout=10) as r2:
            js = r2.read().decode('utf-8', errors='replace')
        hits = re.findall(r'["\'`](/api/[^"\'`\s]{3,100})["\']', js)
        all_routes.update(hits)
        # Also look for fetch( calls with full URLs
        fetches = re.findall(r'fetch\(["\'`]([^"\'`\s]{10,120})["\'`]', js)
        for f in fetches:
            if 'jmail' in f or f.startswith('/'):
                all_routes.add(f)
    except Exception as e:
        pass

print('All API routes found:')
for r in sorted(all_routes):
    print(' ', r)

# Try the turbopuffer search endpoint with a person query
print('\n--- Trying /api/turbopuffer-search for persons ---')
import urllib.parse
payload = json.dumps({'query': 'person', 'type': 'person', 'limit': 100}).encode()
req3 = urllib.request.Request(
    'https://jmail.world/api/turbopuffer-search',
    data=payload,
    headers={**JS_HEADERS, 'content-type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req3, timeout=15) as r3:
        data = json.loads(r3.read())
        print(json.dumps(data, indent=2)[:3000])
except Exception as e:
    print(f'Error: {e}')
