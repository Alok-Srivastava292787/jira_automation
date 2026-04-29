import os
import sys
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

print("Smoke test starting...", flush=True)
load_dotenv()

BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

print("Loaded env vars:", flush=True)
print("BASE_URL =", BASE_URL, flush=True)
print("EMAIL =", EMAIL, flush=True)
print("PROJECT_KEY =", PROJECT_KEY, flush=True)

if not all([BASE_URL, EMAIL, API_TOKEN, PROJECT_KEY]):
    print("ERROR: Missing one or more env vars.", flush=True)
    sys.exit(1)

try:
    print("Calling /myself...", flush=True)
    r = requests.get(
        f"{BASE_URL}/rest/api/3/myself",
        auth=HTTPBasicAuth(EMAIL, API_TOKEN),
        headers={"Accept": "application/json"},
        timeout=30
    )
    print("HTTP status:", r.status_code, flush=True)
    print("Response preview:", r.text[:500], flush=True)

    r.raise_for_status()

    print("Authentication OK", flush=True)

    print("Calling project endpoint...", flush=True)
    r2 = requests.get(
        f"{BASE_URL}/rest/api/3/project/{PROJECT_KEY}",
        auth=HTTPBasicAuth(EMAIL, API_TOKEN),
        headers={"Accept": "application/json"},
        timeout=30
    )
    print("Project status:", r2.status_code, flush=True)
    print("Project response preview:", r2.text[:500], flush=True)
    r2.raise_for_status()

    print("Project access OK", flush=True)

except Exception as e:
    print("ERROR:", repr(e), flush=True)
    sys.exit(2)