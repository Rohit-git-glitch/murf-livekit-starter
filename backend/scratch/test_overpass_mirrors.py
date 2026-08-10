import urllib.request, urllib.parse, json, time

overpass_endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

lat, lon = 19.055, 72.869
query = f'[out:json][timeout:10];(nwr(around:3000,{lat},{lon})[amenity~"hospital|clinic|doctors"];);out center tags 30;'

for ep in overpass_endpoints:
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{ep}?{urllib.parse.urlencode({'data': query})}", headers={"User-Agent": "AarogyaAI-HealthAccess/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            print(f"SUCCESS {ep}: {time.time()-t0:.2f}s, items: {len(data.get('elements', []))}")
    except Exception as e:
        print(f"FAIL {ep}: {time.time()-t0:.2f}s, error: {type(e).__name__} {e}")
