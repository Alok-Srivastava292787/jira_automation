# jira_monitor_board.py
import os, sys, requests
from requests.auth import HTTPBasicAuth
from collections import Counter
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("JIRA_BASE_URL").rstrip('/')
auth = HTTPBasicAuth(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
hdr = {"Accept": "application/json"}

def jget(path, params=None):
    r = requests.get(BASE + path, auth=auth, headers=hdr, params=params)
    r.raise_for_status()
    return r.json()

# 1. Get Scrum board
b = jget("/rest/agile/1.0/board", {"projectKeyOrId": os.getenv("JIRA_PROJECT_KEY"), "type": "scrum"})["values"][0]

# 2. List sprints
sprints = jget(f"/rest/agile/1.0/board/{b['id']}/sprint", {"state": "active,future,closed"})["values"]

# 3. Active sprint issues
active = next((s for s in sprints if s["state"].lower()=="active"), None)
if active:
    issues = jget(f"/rest/agile/1.0/board/{b['id']}/sprint/{active['id']}/issue")["issues"]
    stats = Counter(i["fields"]["status"]["name"] for i in issues)
    print("Active sprint:", active["name"], stats)

# 4. Backlog
backlog = jget(f"/rest/agile/1.0/board/{b['id']}/backlog")["issues"]
print("Backlog:", len(backlog), "issues")
top = backlog[:5]
for i in top:
    f = i["fields"]
    print(i["key"], f["issuetype"]["name"], f["summary"], f["status"]["name"])