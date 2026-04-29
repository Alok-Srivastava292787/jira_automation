### ✅ Prerequisites

*   A valid email to sign up for **Jira Cloud Free** (up to 10 users, 2 GB storage). [\[atlassian.com\]](https://www.atlassian.com/try/cloud/signup), [\[atlassian.com\]](https://www.atlassian.com/software/free)
*   **Python 3.x**, `pip`, and a terminal (PowerShell / CMD / Git Bash / macOS/Linux shell).
*   A user with **Jira Administrator** permissions on the target site (necessary for company‑managed project configuration). [\[bing.com\]](https://bing.com/search?q=site%3aatlassian.com+add+custom+issue+type+Jira+Cloud), [\[support.at...assian.com\]](https://support.atlassian.com/jira-cloud-administration/docs/add-edit-and-delete-an-issue-type/)

***

### 1. 📝 Sign up for Jira Cloud Free

1.  Go to [Atlassian Cloud signup](https://www.atlassian.com/try/cloud/signup) [\[atlassian.com\]](https://www.atlassian.com/try/cloud/signup)
2.  Select **Jira Software**, enter your email, or sign in with Google/Microsoft.
3.  Choose a site name (e.g., `your-team.atlassian.net`).
4.  Verify your email and log in — Congratulations, your free Jira Cloud is ready!

***

### 2. Create a Company‑managed Scrum Project

1.  Click **Create project** in Jira.
2.  Choose **Software development** — then **Scrum**. [\[support.at...assian.com\]](https://support.atlassian.com/jira-software-cloud/docs/what-are-team-managed-and-company-managed-projects/), [\[atlassian.com\]](https://www.atlassian.com/agile/tutorials/how-to-do-scrum-with-jira)
3.  Select **Company‑managed** (allows full configuration control). [\[support.at...assian.com\]](https://support.atlassian.com/jira-software-cloud/docs/what-are-team-managed-and-company-managed-projects/), [\[atlassian.com\]](https://www.atlassian.com/agile/tutorials/how-to-do-scrum-with-jira)
4.  Name it (e.g.,**“AWS DE Learning”**) with key **AWSDL**, make it private or internal.
5.  Click **Create**.

***

### 3. Setup Issue Types (Epic, Story, Task, Bug, Sub‑task, Feature)

1.  Navigate to **Settings → Issues → Work types**. [\[support.at...assian.com\]](https://support.atlassian.com/jira-cloud-administration/docs/add-edit-and-delete-an-issue-type/), [\[support.at...assian.com\]](https://support.atlassian.com/jira-cloud-administration/docs/configure-issue-types/)
2.  Verify default types: **Epic**, **Story**, **Task**, **Bug**, **Sub‑task**.
3.  To add **Feature** as a standard type:
    *   Click **Add work type**
    *   Name it **Feature**, select **Standard**
    *   Save. [\[support.at...assian.com\]](https://support.atlassian.com/jira-cloud-administration/docs/add-edit-and-delete-an-issue-type/), [\[support.at...assian.com\]](https://support.atlassian.com/jira-cloud-administration/docs/configure-issue-types/)
4.  Navigate to **Settings → Work type schemes**:
    *   Edit the scheme your project uses.
    *   Drag **Feature** alongside the other types.
    *   Save. [\[support.at...assian.com\]](https://support.atlassian.com/jira-cloud-administration/docs/add-edit-and-delete-an-issue-type-scheme/), [\[confluence...assian.com\]](https://confluence.atlassian.com/servicedeskcloud/adding-editing-and-deleting-an-issue-type-scheme-1097176108.html)

***

### 4. Assign Proper Access Roles

1.  Open your project → **Project settings → Access (or People/Roles)**.
2.  Add users into roles:
    *   **Project Admin** (you)
    *   **Developer** (contributors, including automation user)
    *   **Stakeholder/viewer** (read-only access)
3.  For your Python script use-case:
    *   Create a **service or automation user**.
    *   Assign it a **Developer** role with **Create**, **Edit**, **Browse** permissions.

***

### 5. Generate an API Token for Script Authentication

1.  Log in to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/signup). [\[docs.adaptavist.com\]](https://docs.adaptavist.com/w4j/latest/quick-configuration-guide/add-sources/how-to-generate-jira-api-token)
2.  Click **Create API token**, name it (e.g. “jira-python-automation”), set expiration, and copy securely.

***

### 6. Create Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate       # bash/macOS/Linux
# or .venv\Scripts\Activate.ps1  # PowerShell
pip install requests python-dotenv
```

Add a `.env` file (do NOT commit):

```dotenv
JIRA_BASE_URL=https://your-site.atlassian.net
JIRA_EMAIL=you@domain.com
JIRA_API_TOKEN=xxxxxxxxxxxxxxxxxxxx
JIRA_PROJECT_KEY=AWSDL
JIRA_BOARD_NAME=AWS DE Learning
```

Add `.env` and `.venv/` to `.gitignore`.

***

### 7. 📌 Script A: Create Sample Issues via REST API

```python
# jira_create_sample_issues.py
import os, sys, json, requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("JIRA_BASE_URL").rstrip('/')
auth = HTTPBasicAuth(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
hdr = {"Accept": "application/json", "Content-Type": "application/json"}

def jget(path, params=None):
    r = requests.get(BASE + path, auth=auth, headers=hdr, params=params)
    r.raise_for_status()
    return r.json()

def jpost(path, data):
    r = requests.post(BASE + path, auth=auth, headers=hdr, data=json.dumps(data))
    r.raise_for_status()
    return r.json()

def create_issue(typ, summary, desc, parent=None, epic_name=None):
    payload = {
        "fields": {
            "project": {"key": os.getenv("JIRA_PROJECT_KEY")},
            "issuetype": {"name": typ},
            "summary": summary,
            "description": desc
        }
    }
    if typ.lower() == "epic" and epic_name:
        payload["fields"]["customfield_10011"] = epic_name  # adjust for your site
    if parent:
        payload["fields"]["parent"] = {"key": parent}
    return jpost("/rest/api/3/issue", payload)["key"]

print("Connected as:", jget("/rest/api/3/myself")["displayName"])
epic = create_issue("Epic", "[Auto] Platform MVP", "Created via script", epic_name="PEPIC")
feature = create_issue("Feature", "[Auto] Ingestion", "Feature via script")
story = create_issue("Story", "[Auto] Landing zone", "Story linked", parent=epic)
task = create_issue("Task", "[Auto] IAM roles", "Task linked", parent=epic)
bug = create_issue("Bug", "[Auto] STS fix", "Bug linked", parent=epic)
sub = create_issue("Sub-task", "[Auto] Validate IAM", "Sub-task for task", parent=task)

print("Created keys:", epic, feature, story, task, bug, sub)
```

*   Use `/rest/api/3/myself` to verify authentication.
*   Use `customfield_10011` (Epic Name) — verify field ID via `/rest/api/3/field`. [\[developer....assian.com\]](https://developer.atlassian.com/server/jira/platform/jira-rest-api-examples/)

***

### 8. 📊 Script B: Backlog & Sprint Monitoring

```python
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
```

*   Uses `/rest/agile/1.0/...` endpoints. [\[developer....assian.com\]](https://developer.atlassian.com/cloud/jira/software/rest/api-group-backlog/)
*   Summarizes active sprint and shows top backlog issues.

***

### 🔧 Next Steps You Didn’t Ask Explicitly

*   Create an initial sprint in Jira UI: click **Backlog → Create Sprint**, drag relevant issues, and **Start Sprint**.
*   Schedule these Python scripts to run automatically using cron / Task Scheduler or CI/CD for daily reporting.
*   If your team grows beyond 10 users, consider Jira Standard or Premium for hierarchy and advanced workflows.

***

These steps and scripts give you a **complete playbook** to set up a free Scrum-ready Jira project and automate both issue creation and monitoring from Python.Would you like this playbook packaged as a **Git repo template** or converted into a **one‑page runbook PDF**?
