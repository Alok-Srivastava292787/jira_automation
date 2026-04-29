import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

if not all([BASE_URL, EMAIL, API_TOKEN, PROJECT_KEY]):
    print("ERROR: Missing env vars.", flush=True)
    sys.exit(1)

session = requests.Session()
session.auth = HTTPBasicAuth(EMAIL, API_TOKEN)
session.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json"
})

def adf_text(text):
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}]
            }
        ]
    }

def get(path, params=None):
    r = session.get(f"{BASE_URL}{path}", params=params, timeout=30)
    print(f"GET {path} -> {r.status_code}", flush=True)
    if not r.ok:
        print(r.text[:1000], flush=True)
        r.raise_for_status()
    return r.json()

def post(path, payload):
    r = session.post(f"{BASE_URL}{path}", data=json.dumps(payload), timeout=30)
    print(f"POST {path} -> {r.status_code}", flush=True)
    print("Response:", r.text[:1000], flush=True)
    if not r.ok:
        r.raise_for_status()
    return r.json()

def get_issue_types_for_project():
    project = get(f"/rest/api/3/project/{PROJECT_KEY}")
    return {it["name"].lower(): it for it in project.get("issueTypes", [])}

def get_fields():
    return get("/rest/api/3/field")

def find_field_id(fields, field_name):
    for f in fields:
        if f.get("name", "").strip().lower() == field_name.strip().lower():
            return f["id"]
    return None

def create_issue(issue_type_name, summary, description, parent_key=None, extra_fields=None):
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "issuetype": {"name": issue_type_name},
            "description": adf_text(description)
        }
    }

    if parent_key:
        payload["fields"]["parent"] = {"key": parent_key}

    if extra_fields:
        payload["fields"].update(extra_fields)

    print(f"\nCreating {issue_type_name}: {summary}", flush=True)
    print(json.dumps(payload, indent=2), flush=True)

    result = post("/rest/api/3/issue", payload)
    return result["key"]

def main():
    print("Verifying authentication...", flush=True)
    me = get("/rest/api/3/myself")
    print("Authenticated as:", me.get("displayName"), flush=True)

    print("Loading project issue types...", flush=True)
    issue_types = get_issue_types_for_project()
    print("Available issue types:", list(issue_types.keys()), flush=True)

    fields = get_fields()
    epic_name_field_id = find_field_id(fields, "Epic Name")
    print("Epic Name field:", epic_name_field_id, flush=True)

    # 1. Task
    task_key = create_issue(
        "Task",
        "[Automation Demo] Create a simple task",
        "This is a task created by Python automation."
    )

    # 2. Epic
    epic_key = None
    if "epic" in issue_types:
        extra = {}
        if epic_name_field_id:
            extra[epic_name_field_id] = "AUTODEMOEPIC"
        epic_key = create_issue(
            "Epic",
            "[Automation Demo] Platform MVP",
            "Epic created by Python automation.",
            extra_fields=extra
        )

    # 3. Story (plain first; linking to Epic varies by site config)
    story_key = None
    if "story" in issue_types:
        story_key = create_issue(
            "Story",
            "[Automation Demo] Build landing zone",
            "Story created by Python automation."
        )

    # 4. Bug
    bug_key = None
    if "bug" in issue_types:
        bug_key = create_issue(
            "Bug",
            "[Automation Demo] Fix pipeline auth issue",
            "Bug created by Python automation."
        )

    # 5. Sub-task under Task
    subtask_key = None
    if "sub-task" in issue_types:
        subtask_key = create_issue(
            "Sub-task",
            "[Automation Demo] Validate task details",
            "Sub-task created under Task.",
            parent_key=task_key
        )

    # 6. Feature (only if available)
    feature_key = None
    if "feature" in issue_types:
        feature_key = create_issue(
            "Feature",
            "[Automation Demo] Data ingestion framework",
            "Feature created by Python automation."
        )

    print("\n=== Created issues ===", flush=True)
    print("Task    :", task_key, flush=True)
    print("Epic    :", epic_key, flush=True)
    print("Story   :", story_key, flush=True)
    print("Bug     :", bug_key, flush=True)
    print("Sub-task:", subtask_key, flush=True)
    print("Feature :", feature_key, flush=True)

if __name__ == "__main__":
    main()
