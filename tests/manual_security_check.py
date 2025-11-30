import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_security():
    print("Waiting for server to start...")
    for i in range(10):
        try:
            requests.get(f"{BASE_URL}/health", timeout=1)
            break
        except:
            time.sleep(1)
            print(f"Retrying... {i}")
    else:
        print("Server did not start in time.")
        sys.exit(1)

    print("Server is up. Running tests...")

    # 1. No token
    try:
        r = requests.get(f"{BASE_URL}/config")
        print(f"No token (config): {r.status_code}")
        if r.status_code != 401:
             print("FAIL: Expected 401 for no token")
    except Exception as e:
        print(f"No token error: {e}")

    # 2. Viewer token
    headers_viewer = {"Authorization": "Bearer viewer_secret"}
    r = requests.get(f"{BASE_URL}/config", headers=headers_viewer)
    print(f"Viewer token (config): {r.status_code}")
    if r.status_code != 200:
         print("FAIL: Expected 200 for viewer token on /config")

    # 3. Admin token
    headers_admin = {"Authorization": "Bearer admin_secret"}
    r = requests.get(f"{BASE_URL}/config", headers=headers_admin)
    print(f"Admin token (config): {r.status_code}")
    if r.status_code != 200:
         print("FAIL: Expected 200 for admin token on /config")

    # 4. Run command (requires admin)
    # Note: /run is a POST
    r = requests.post(f"{BASE_URL}/run", json={"command": ["echo", "hello"]}, headers=headers_viewer)
    print(f"Viewer token (run): {r.status_code}")
    if r.status_code != 403:
         print("FAIL: Expected 403 for viewer token on /run")

    r = requests.post(f"{BASE_URL}/run", json={"command": ["echo", "hello"]}, headers=headers_admin)
    print(f"Admin token (run): {r.status_code}")
    if r.status_code != 200:
         print(f"FAIL: Expected 200 for admin token on /run, got {r.status_code}")
         print(r.text)

    print("SECURITY_CHECK_PASSED")

if __name__ == "__main__":
    test_security()
