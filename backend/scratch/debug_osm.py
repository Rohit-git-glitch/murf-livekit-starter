import sys, logging
sys.path.insert(0, 'src')
from health_access import find_nearby_health_facilities, _request_json, NOMINATIM_URL, OVERPASS_URL

logging.basicConfig(level=logging.DEBUG)
print("Testing Nominatim...")
try:
    geo = _request_json(NOMINATIM_URL, {"q": "Mumbai, India", "format": "jsonv2", "limit": "1"})
    print("Geocoded:", geo)
    lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
    print("Testing Overpass...")
    query = f'[out:json][timeout:5];(nwr(around:3000,{lat},{lon})[amenity~"hospital|clinic|doctors"];);out center tags 30;'
    op = _request_json(OVERPASS_URL, {"data": query})
    print("Overpass success! Elements count:", len(op.get("elements", [])))
except Exception as e:
    print("EXCEPT:", type(e), e)
