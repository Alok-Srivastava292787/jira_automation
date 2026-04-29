import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

print("Create-task script starting...", flush=True)
load_dotenv()

BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

if not all([BASE_URL, EMAIL, API_TOKEN, PROJECT_KEY]):
    print("ERROR: Missing env vars.", flush=True)
    sys.exit(1)

def adf_text(text):
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }
        ]
    }

payload = {
    "fields": {
        "project": {"key": PROJECT_KEY},
        "summary": "[Smoke Test] Create simple task from Python",
        "issuetype": {"name": "Task"},
        "description": adf_text("This task was created successfully using Jira REST API from Python.")
    }
}

print("Request payload:", json.dumps(payload, indent=2), flush=True)

try:
    r = requests.post(
        f"{BASE_URL}/rest/api/3/issue",
        auth=HTTPBasicAuth(EMAIL, API_TOKEN),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        data=json.dumps(payload),
        timeout=30
    )

    print("HTTP status:", r.status_code, flush=True)
    print("Response:", r.text[:1000], flush=True)

    r.raise_for_status()

    result = r.json()
    print(f"SUCCESS: Issue created -> {result['key']}", flush=True)

except Exception as e:
    print("ERROR:", repr(e), flush=True)
    sys.exit(2)
