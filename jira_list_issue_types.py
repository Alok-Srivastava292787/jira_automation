import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

r = requests.get(
    f"{BASE_URL}/rest/api/3/project/{PROJECT_KEY}",
    auth=HTTPBasicAuth(EMAIL, API_TOKEN),
    headers={"Accept": "application/json"},
    timeout=30
)

r.raise_for_status()
project = r.json()

print("Issue types available in project:")
for it in project.get("issueTypes", []):
    print("-", it["name"], f"(id={it['id']})")
    
