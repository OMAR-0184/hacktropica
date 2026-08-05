import json
import urllib.request
import urllib.error

url = "http://localhost:8002/learning/40eddd9a-ea50-4efb-bea4-95925751a926/continue"

try:
    req = urllib.request.Request(
        url,
        data=json.dumps({"selected_node": "Intro to Python", "traversal_mode": "dfs"}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer cognimap_access_token"} # Use a dummy token, it might give 401 instead, but let's try.
    )
    urllib.request.urlopen(req)
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Body: {e.read().decode()}")

