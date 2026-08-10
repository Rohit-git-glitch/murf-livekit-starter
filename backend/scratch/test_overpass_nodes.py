import urllib.request, urllib.parse, json, time

overpass_endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass.knet.cn/api/interpreter",
]

lat, lon = 19.055, 72.869

# Optimized node-only query for speed
query_nodes = f'[out:json][timeout:5];node(around:2000,{lat},{lon})[amenity~"hospital|clinic|doctors"];out tags 15;'

for ep in overpass_endpoints:
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{ep}?{urllib.parse.urlencode({'data': query_nodes})}", headers={"User-Agent": "AarogyaAI-HealthAccess/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"SUCCESS {ep}: {time.time()-t0:.2f}s, items: {len(data.get('elements', []))}")
    except Exception as e:
        print(f"FAIL {ep}: {time.time()-t0:.2f}s, error: {type(e).__name__} {e}")
