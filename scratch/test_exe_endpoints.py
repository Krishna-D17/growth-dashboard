import urllib.request
import urllib.error
import json

def test_executable_http():
    print("=== TESTING EXECUTABLE HTTP ENDPOINTS ===")
    
    # 1. Health Endpoint
    health_url = "http://127.0.0.1:8000/health"
    req = urllib.request.Request(health_url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print("GET /health status:", resp.status, "data:", data)
        assert resp.status == 200
        assert data["status"] == "ok"

    # 2. Profiles Endpoint
    profiles_url = "http://127.0.0.1:8000/api/profiles"
    req_p = urllib.request.Request(profiles_url)
    with urllib.request.urlopen(req_p) as resp_p:
        profs = json.loads(resp_p.read().decode())
        print("GET /api/profiles status:", resp_p.status, "count:", len(profs))
        assert resp_p.status == 200

    # 3. Frontend Static SPA Index Page
    index_url = "http://127.0.0.1:8000/"
    req_i = urllib.request.Request(index_url)
    with urllib.request.urlopen(req_i) as resp_i:
        html = resp_i.read().decode()
        print("GET / status:", resp_i.status, "HTML snippet:", html[:120].strip())
        assert resp_i.status == 200
        assert "<!doctype html>" in html.lower() or "<html" in html.lower()

    # 4. Frontend SPA Client Route Fallback
    spa_url = "http://127.0.0.1:8000/comparison"
    req_s = urllib.request.Request(spa_url)
    with urllib.request.urlopen(req_s) as resp_s:
        spa_html = resp_s.read().decode()
        print("GET /comparison (SPA fallback) status:", resp_s.status, "HTML snippet:", spa_html[:120].strip())
        assert resp_s.status == 200
        assert "<!doctype html>" in spa_html.lower() or "<html" in spa_html.lower()

if __name__ == "__main__":
    test_executable_http()
