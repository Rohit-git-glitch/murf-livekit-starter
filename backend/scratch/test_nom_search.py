import urllib.request, urllib.parse, json

loc = "Mumbai"
req1 = urllib.request.Request(f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(loc + ', India')}&format=jsonv2&limit=1", headers={"User-Agent": "AarogyaAI-HealthAccess/1.0"})
with urllib.request.urlopen(req1, timeout=5) as r:
    g = json.loads(r.read())
    lat, lon = float(g[0]["lat"]), float(g[0]["lon"])
    print("Geocoded OK:", lat, lon)

req2 = urllib.request.Request(f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote('hospital near ' + loc + ', India')}&format=jsonv2&limit=5", headers={"User-Agent": "AarogyaAI-HealthAccess/1.0"})
with urllib.request.urlopen(req2, timeout=5) as r:
    h = json.loads(r.read())
    print("Nominatim Direct Hospitals found:", len(h))
    for item in h[:3]:
        print(" -", item.get("display_name"))
