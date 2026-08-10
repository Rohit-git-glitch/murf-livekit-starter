import urllib.request, urllib.parse, json

lat, lon = 19.055, 72.869
# Querying node, way, relation using simplified tags
q1 = f'[out:json][timeout:5];nwr(around:3000,{lat},{lon})[amenity=hospital];out center tags 10;'
q2 = f'[out:json][timeout:5];node(around:3000,{lat},{lon})[healthcare];out tags 10;'

for q in [q1, q2]:
    try:
        url = f"https://overpass-api.de/api/interpreter?{urllib.parse.urlencode({'data': q})}"
        req = urllib.request.Request(url, headers={"User-Agent": "AarogyaAI-HealthAccess/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            d = json.loads(resp.read().decode())
            print("QUERY OK, elements:", len(d.get("elements", [])))
    except Exception as e:
        print("QUERY FAIL:", type(e), e)
