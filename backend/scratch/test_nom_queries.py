import urllib.request, urllib.parse, json

queries = ["hospital, Mumbai, India", "clinic, Mumbai, India", "health, Mumbai, India"]
for q in queries:
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=jsonv2&limit=3"
    req = urllib.request.Request(url, headers={"User-Agent": "AarogyaAI-HealthAccess/1.0"})
    with urllib.request.urlopen(req, timeout=5) as r:
        res = json.loads(r.read())
        print(f"QUERY '{q}' returned:", len(res))
        for item in res:
            print(" -", item.get("name") or item.get("display_name", "").split(",")[0], "|", item.get("display_name"))
