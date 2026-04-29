import os
import re
import sys
import json
import argparse
from typing import Dict, List, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv


# ============================================================
# Utility helpers
# ============================================================

def log(msg: str):
    print(msg, flush=True)


def normalize_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.strip().lower()).strip()


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def split_code_and_title(value: str) -> Tuple[str, str]:
    """
    Example:
      'EP-01: Environment & Foundations'
      -> ('EP-01', 'Environment & Foundations')
    If no colon exists, returns (value, value)
    """
    if ":" in value:
        left, right = value.split(":", 1)
        return left.strip(), right.strip()
    return value.strip(), value.strip()


def adf_paragraphs(paragraphs: List[str]) -> Dict:
    """
    Jira Cloud REST v3 expects ADF for description/textarea fields.
    """
    content = []
    for p in paragraphs:
        p = (p or "").strip()
        if not p:
            continue
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": p}]
        })

    if not content:
        content = [{
            "type": "paragraph",
            "content": [{"type": "text", "text": ""}]
        }]

    return {
        "type": "doc",
        "version": 1,
        "content": content
    }


# ============================================================
# Markdown parsing
# ============================================================

def is_jira_card_heading(line: str) -> bool:
    """
    Very tolerant heading detection.
    Accepts:
      JIRA CARD
      🗂️ JIRA CARD
      ## JIRA CARD
      ## 🗂️ JIRA CARD
    """
    if not line:
        return False

    cleaned = line.strip().upper()

    # remove markdown heading markers
    cleaned = re.sub(r"^#+\s*", "", cleaned)

    # normalize spaces
    cleaned = re.sub(r"\s+", " ", cleaned)

    return "JIRA CARD" in cleaned


def parse_table_line(line: str):
    """
    Supports:
      1) pipe table: | Field | Value |
      2) tab table:  Field<TAB>Value
      3) spaced row: Field    Value
    """
    raw = line.strip()
    if not raw:
        return None

    # Ignore markdown separator lines
    if set(raw.replace("|", "").replace(":", "").replace("-", "").replace(" ", "")) == set():
        return None

    # Pipe table
    if "|" in raw:
        parts = [p.strip() for p in raw.strip("|").split("|")]
        if len(parts) >= 2:
            return parts[0], "|".join(parts[1:]).strip()

    # Tab separated
    if "\t" in raw:
        parts = [p.strip() for p in raw.split("\t") if p.strip()]
        if len(parts) >= 2:
            return parts[0], " ".join(parts[1:]).strip()

    # 2+ spaces separated
    parts = re.split(r"\s{2,}", raw, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()

    return None


def parse_jira_cards_from_markdown(md_text: str):
    """
    Finds one or more JIRA CARD sections in markdown.
    """
    lines = md_text.splitlines()
    cards = []
    i = 0

    while i < len(lines):
        if is_jira_card_heading(lines[i]):
            i += 1

            # skip blank lines after heading
            while i < len(lines) and not lines[i].strip():
                i += 1

            card = {}

            while i < len(lines):
                line = lines[i]

                # stop if next heading starts
                if is_jira_card_heading(line) and card:
                    break

                # stop if normal markdown heading starts after table began
                if re.match(r"^\s*#{1,6}\s+", line) and card:
                    break

                parsed = parse_table_line(line)
                if parsed:
                    key, value = parsed

                    # skip header row
                    if key.strip().lower() == "field" and value.strip().lower() == "value":
                        i += 1
                        continue

                    card[key.strip()] = value.strip()
                else:
                    # if table already started, stop at first non-table row
                    if card:
                        break

                i += 1

            if card:
                cards.append(card)
            continue

        i += 1

    return cards

def card_get(card: Dict[str, str], *names: str) -> Optional[str]:
    norm_map = {normalize_key(k): v for k, v in card.items()}
    for n in names:
        val = norm_map.get(normalize_key(n))
        if val is not None:
            return val
    return None


# ============================================================
# Jira client
# ============================================================

class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str, verify=True):
        self.base_url = base_url.rstrip("/")
        self.verify = verify

        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(email, api_token)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def get(self, path: str, params=None):
        r = self.session.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=30,
            verify=self.verify
        )
        if not r.ok:
            log(f"[GET] {path} -> {r.status_code}")
            log(r.text[:2000])
            r.raise_for_status()
        return r.json()

    def post(self, path: str, payload: Dict):
        r = self.session.post(
            f"{self.base_url}{path}",
            json=payload,
            timeout=30,
            verify=self.verify
        )
        if not r.ok:
            log(f"[POST] {path} -> {r.status_code}")
            log("Payload:")
            log(json.dumps(payload, indent=2, ensure_ascii=False))
            log("Response:")
            log(r.text[:3000])
            r.raise_for_status()
        return r.json() if r.text else {}

    def verify_connection(self):
        return self.get("/rest/api/3/myself")

    def get_project(self, project_key: str):
        return self.get(f"/rest/api/3/project/{project_key}")

    def get_fields(self):
        return self.get("/rest/api/3/field")

    def get_priorities(self):
        try:
            data = self.get("/rest/api/3/priority/search")
            return data.get("values", [])
        except Exception:
            data = self.get("/rest/api/3/priority")
            return data if isinstance(data, list) else data.get("values", [])

    def search_users(self, query: str):
        try:
            return self.get("/rest/api/3/user/search", params={"query": query, "maxResults": 20})
        except Exception:
            return []

    def get_transitions(self, issue_key: str):
        data = self.get(f"/rest/api/3/issue/{issue_key}/transitions")
        return data.get("transitions", [])

    def transition_issue(self, issue_key: str, transition_id: str):
        self.post(f"/rest/api/3/issue/{issue_key}/transitions", {"transition": {"id": transition_id}})

    def get_boards(self, project_key: str):
        data = self.get("/rest/agile/1.0/board", params={"projectKeyOrId": project_key, "type": "scrum"})
        return data.get("values", [])

    def get_sprints_for_board(self, board_id: int):
        data = self.get(f"/rest/agile/1.0/board/{board_id}/sprint", params={"state": "active,future"})
        return data.get("values", [])


# ============================================================
# Jira metadata helpers
# ============================================================

def find_field_id(fields: List[Dict], candidate_names: List[str]) -> Optional[str]:
    candidates = {normalize_key(x) for x in candidate_names}
    for f in fields:
        if normalize_key(f.get("name", "")) in candidates:
            return f["id"]
    return None


def resolve_priority_name(requested_priority: Optional[str], priorities: List[Dict]) -> Optional[str]:
    """
    Jira site is expecting priority as STRING, not {"name": "..."} for your setup.
    We resolve the input against actual site priorities.
    """
    if not requested_priority:
        return None

    requested = requested_priority.strip().lower()
    available_names = [p.get("name", "") for p in priorities]

    # Exact match first
    for name in available_names:
        if name.lower() == requested:
            return name

    # Friendly aliases
    alias_map = {
        "critical": ["Critical", "Highest", "High", "Major"],
        "highest": ["Highest"],
        "high": ["High", "Highest", "Major"],
        "medium": ["Medium", "Normal", "Major"],
        "normal": ["Normal", "Medium"],
        "low": ["Low", "Minor", "Lowest"],
        "lowest": ["Lowest", "Low", "Minor"],
    }

    for candidate in alias_map.get(requested, []):
        for actual in available_names:
            if actual.lower() == candidate.lower():
                return actual

    return None


def resolve_assignee_account_id(jira: JiraClient, assignee_value: Optional[str]) -> Optional[str]:
    if not assignee_value:
        return None

    val = assignee_value.strip()
    if not val:
        return None

    # Ignore placeholders like [Your Name]
    if val.startswith("[") and val.endswith("]"):
        return None

    users = jira.search_users(val)
    if not users:
        return None

    # Prefer exact display name or exact email match
    val_norm = val.lower()
    for u in users:
        display = (u.get("displayName") or "").lower()
        email = (u.get("emailAddress") or "").lower()
        if val_norm == display or val_norm == email:
            return u.get("accountId")

    return users[0].get("accountId")


def find_sprint_id(jira: JiraClient, project_key: str, sprint_name: Optional[str], board_name: Optional[str] = None) -> Optional[int]:
    if not sprint_name:
        return None

    boards = jira.get_boards(project_key)
    if board_name:
        filtered = [b for b in boards if normalize_key(b.get("name", "")) == normalize_key(board_name)]
        if filtered:
            boards = filtered

    for board in boards:
        sprints = jira.get_sprints_for_board(board["id"])
        for s in sprints:
            if normalize_key(s.get("name", "")) == normalize_key(sprint_name):
                return s["id"]
    return None


def find_transition_id(transitions: List[Dict], desired_status: str) -> Optional[str]:
    desired = normalize_key(desired_status)

    for t in transitions:
        to_name = normalize_key(t.get("to", {}).get("name", ""))
        if to_name == desired:
            return t["id"]

    for t in transitions:
        t_name = normalize_key(t.get("name", ""))
        if t_name == desired:
            return t["id"]

    return None


# ============================================================
# Jira issue creation helpers
# ============================================================

def create_issue(
    jira: JiraClient,
    project_key: str,
    issue_type_name: str,
    summary: str,
    description: Dict,
    parent_key: Optional[str] = None,
    extra_fields: Optional[Dict] = None
) -> str:
    fields = {
        "project": {"key": project_key},
        "issuetype": {"name": issue_type_name},
        "summary": summary,
        "description": description
    }

    if parent_key:
        fields["parent"] = {"key": parent_key}

    if extra_fields:
        fields.update(extra_fields)

    payload = {"fields": fields}
    result = jira.post("/rest/api/3/issue", payload)
    return result["key"]


def create_story_linked_to_epic(
    jira: JiraClient,
    project_key: str,
    summary: str,
    description: Dict,
    epic_key: str,
    extra_fields: Dict,
    epic_link_field_id: Optional[str]
) -> str:
    # Preferred modern Jira Cloud style
    try:
        return create_issue(
            jira=jira,
            project_key=project_key,
            issue_type_name="Story",
            summary=summary,
            description=description,
            parent_key=epic_key,
            extra_fields=extra_fields
        )
    except requests.HTTPError:
        # Fallback for older / compatible field behavior
        if epic_link_field_id:
            fields = dict(extra_fields)
            fields[epic_link_field_id] = epic_key
            return create_issue(
                jira=jira,
                project_key=project_key,
                issue_type_name="Story",
                summary=summary,
                description=description,
                parent_key=None,
                extra_fields=fields
            )
        raise


def transition_if_possible(jira: JiraClient, issue_key: str, desired_status: Optional[str]):
    if not desired_status:
        return

    transitions = jira.get_transitions(issue_key)
    t_id = find_transition_id(transitions, desired_status)
    if t_id:
        jira.transition_issue(issue_key, t_id)
        log(f"Transitioned {issue_key} -> {desired_status}")
    else:
        log(f"WARNING: No matching transition found for {issue_key} -> {desired_status}")


# ============================================================
# Build per-card fields
# ============================================================

def build_story_description(card: Dict[str, str]) -> Dict:
    paragraphs = []

    story_val = card_get(card, "Story")
    task_id = card_get(card, "Task ID", "Task Id", "TaskID")
    sprint = card_get(card, "Sprint")
    labels = card_get(card, "Labels")
    acceptance = card_get(card, "Acceptance Criteria", "Acceptance criteria")

    if story_val:
        paragraphs.append(f"Story source: {story_val}")
    if task_id:
        paragraphs.append(f"Task ID: {task_id}")
    if sprint:
        paragraphs.append(f"Sprint: {sprint}")
    if labels:
        paragraphs.append(f"Labels: {labels}")
    if acceptance:
        paragraphs.append(f"Acceptance Criteria: {acceptance}")

    return adf_paragraphs(paragraphs)


# ============================================================
# Main processing per card
# ============================================================

def process_card(
    jira: JiraClient,
    project_key: str,
    project: Dict,
    fields: List[Dict],
    priorities: List[Dict],
    card: Dict[str, str],
    board_name: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Optional[str]]:

    epic_val = card_get(card, "Epic")
    story_val = card_get(card, "Story")
    task_id_val = card_get(card, "Task ID", "Task Id", "TaskID")
    status_val = card_get(card, "Status")
    sprint_val = card_get(card, "Sprint")
    assignee_val = card_get(card, "Assignee")
    labels_val = card_get(card, "Labels")
    acceptance_val = card_get(card, "Acceptance Criteria", "Acceptance criteria")
    story_points_val = card_get(card, "Story Points", "Story point", "Story point estimate")
    priority_val = card_get(card, "Priority")

    if not epic_val or not story_val:
        raise ValueError("Each JIRA CARD must contain at least 'Epic' and 'Story'.")

    available_issue_types = {normalize_key(it["name"]) for it in project.get("issueTypes", [])}

    if "epic" not in available_issue_types:
        raise RuntimeError("Epic issue type is not available in this project.")
    if "story" not in available_issue_types:
        raise RuntimeError("Story issue type is not available in this project.")
    if "sub task" not in available_issue_types and "sub-task" not in available_issue_types:
        log("WARNING: Sub-task issue type is not available in this project. Task ID will be ignored.")

    field_ids = {
        "epic_name": find_field_id(fields, ["Epic Name"]),
        "epic_link": find_field_id(fields, ["Epic Link"]),
        "story_points": find_field_id(fields, ["Story Points", "Story point estimate", "Story point estimate (new)"]),
        "sprint": find_field_id(fields, ["Sprint"]),
        "acceptance_criteria": find_field_id(fields, ["Acceptance Criteria", "Acceptance criteria"])
    }

    assignee_account_id = resolve_assignee_account_id(jira, assignee_val)
    sprint_id = find_sprint_id(jira, project_key, sprint_val, board_name=board_name)
    resolved_priority_name = resolve_priority_name(priority_val, priorities)

    if priority_val:
        if resolved_priority_name:
            log(f"Resolved priority: {priority_val} -> {resolved_priority_name}")
        else:
            log(f"WARNING: Priority '{priority_val}' not found in Jira; priority will be skipped.")

    labels = [slugify(x) for x in labels_val.split(",")] if labels_val else []
    story_description = build_story_description(card)

    epic_code, _ = split_code_and_title(epic_val)

    epic_fields = {}
    if field_ids["epic_name"]:
        epic_fields[field_ids["epic_name"]] = epic_code[:255]

    # Optional fields on epic as well
    if labels:
        epic_fields["labels"] = labels
    if assignee_account_id:
        epic_fields["assignee"] = {"accountId": assignee_account_id}
    if resolved_priority_name:
        epic_fields["priority"] = resolved_priority_name  # <-- plain string for your site

    # Story fields
    story_fields = {}

    if labels:
        story_fields["labels"] = labels
    if assignee_account_id:
        story_fields["assignee"] = {"accountId": assignee_account_id}
    if resolved_priority_name:
        story_fields["priority"] = resolved_priority_name  # <-- plain string for your site
    if sprint_id and field_ids["sprint"]:
        story_fields[field_ids["sprint"]] = sprint_id
    if story_points_val and field_ids["story_points"]:
        try:
            story_fields[field_ids["story_points"]] = int(story_points_val)
        except ValueError:
            try:
                story_fields[field_ids["story_points"]] = float(story_points_val)
            except ValueError:
                log(f"WARNING: Story Points '{story_points_val}' is not numeric; skipped.")
    if acceptance_val and field_ids["acceptance_criteria"]:
        story_fields[field_ids["acceptance_criteria"]] = adf_paragraphs([acceptance_val])

    subtask_fields = {}
    if labels:
        subtask_fields["labels"] = labels
    if assignee_account_id:
        subtask_fields["assignee"] = {"accountId": assignee_account_id}
    if resolved_priority_name:
        subtask_fields["priority"] = resolved_priority_name  # <-- plain string for your site
    if sprint_id and field_ids["sprint"]:
        subtask_fields[field_ids["sprint"]] = sprint_id

    if dry_run:
        return {
            "epic_summary": epic_val,
            "story_summary": story_val,
            "subtask_summary": task_id_val
        }

    # 1) Epic
    epic_key = create_issue(
        jira=jira,
        project_key=project_key,
        issue_type_name="Epic",
        summary=epic_val,
        description=adf_paragraphs([
            f"Epic source: {epic_val}",
            "Generated from Markdown JIRA CARD"
        ]),
        extra_fields=epic_fields
    )
    log(f"✅ Epic created: {epic_key}")

    # 2) Story linked to Epic
    story_key = create_story_linked_to_epic(
        jira=jira,
        project_key=project_key,
        summary=story_val,
        description=story_description,
        epic_key=epic_key,
        extra_fields=story_fields,
        epic_link_field_id=field_ids["epic_link"]
    )
    log(f"✅ Story created: {story_key} -> Epic {epic_key}")

    # 3) Sub-task under Story using Task ID
    subtask_key = None
    if task_id_val and ("sub task" in available_issue_types or "sub-task" in available_issue_types):
        subtask_key = create_issue(
            jira=jira,
            project_key=project_key,
            issue_type_name="Sub-task",
            summary=task_id_val,
            description=adf_paragraphs([
                f"Task ID: {task_id_val}",
                f"Parent Story: {story_val}"
            ]),
            parent_key=story_key,
            extra_fields=subtask_fields
        )
        log(f"✅ Sub-task created: {subtask_key} -> Story {story_key}")

    # 4) Transition status if possible
    if status_val:
        try:
            transition_if_possible(jira, story_key, status_val)
        except Exception as e:
            log(f"WARNING: Could not transition Story {story_key} -> {status_val}: {e}")

        if subtask_key:
            try:
                transition_if_possible(jira, subtask_key, status_val)
            except Exception as e:
                log(f"WARNING: Could not transition Sub-task {subtask_key} -> {status_val}: {e}")

    return {
        "epic": epic_key,
        "story": story_key,
        "subtask": subtask_key
    }


# ============================================================
# Entry point
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Create Jira Epic -> Story -> Sub-task from Markdown JIRA CARD sections."
    )
    parser.add_argument("markdown_file", help="Path to markdown file")
    parser.add_argument("--project-key", help="Override JIRA_PROJECT_KEY")
    parser.add_argument("--board-name", help="Optional board name to help sprint resolution")
    parser.add_argument("--verify", help="Optional CA bundle path if your network needs it")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not create Jira issues")
    args = parser.parse_args()

    load_dotenv()

    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")
    project_key = args.project_key or os.getenv("JIRA_PROJECT_KEY")
    verify_bundle = args.verify or os.getenv("JIRA_VERIFY_BUNDLE")

    if not all([base_url, email, token, project_key]):
        raise RuntimeError("Missing required config in .env")

    verify = verify_bundle if verify_bundle else True

    with open(args.markdown_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    cards = parse_jira_cards_from_markdown(md_text)
    if not cards:
        raise RuntimeError("No JIRA CARD section found in markdown file")

    jira = JiraClient(base_url, email, token, verify=verify)

    me = jira.verify_connection()
    log(f"Connected as: {me.get('displayName')}")

    project = jira.get_project(project_key)
    log(f"Project: {project['key']} - {project['name']}")

    fields = jira.get_fields()
    priorities = jira.get_priorities()

    log("Available Jira priorities:")
    for p in priorities:
        log(f" - {p.get('name')}")

    results = []

    for idx, card in enumerate(cards, start=1):
        log("\n" + "=" * 72)
        log(f"Processing JIRA CARD #{idx}")
        log(json.dumps(card, indent=2, ensure_ascii=False))

        try:
            result = process_card(
                jira=jira,
                project_key=project_key,
                project=project,
                fields=fields,
                priorities=priorities,
                card=card,
                board_name=args.board_name,
                dry_run=args.dry_run
            )
            results.append(result)
        except Exception as e:
            log(f"ERROR while processing card #{idx}: {e}")
            results.append({"error": str(e)})

    log("\n" + "=" * 72)
    log("Summary")
    for idx, res in enumerate(results, start=1):
        log(f"Card #{idx}: {res}")


if __name__ == "__main__":
    main()