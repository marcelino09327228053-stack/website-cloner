from pathlib import Path
from datetime import datetime
import json

BASE = Path(__file__).resolve().parent
REGISTRY = BASE / "projects.json"

def safe_folder_name(value):
    value = (value or "New Website").strip()
    forbidden = '<>:"/\\|?*'
    for ch in forbidden:
        value = value.replace(ch, "-")
    value = value.rstrip(". ")
    return value or "New Website"

def load_projects():
    if not REGISTRY.exists():
        return []
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_projects(projects):
    REGISTRY.write_text(json.dumps(projects, indent=2, ensure_ascii=False), encoding="utf-8")

def register_project(project_path, display_name=None):
    path = Path(project_path).expanduser().resolve()
    now = datetime.now().isoformat(timespec="seconds")
    projects = load_projects()
    key = str(path).casefold()
    existing = next((x for x in projects if str(x.get("project_path", "")).casefold() == key), None)
    if existing:
        existing["display_name"] = display_name or existing.get("display_name") or path.name
        existing["updated_at"] = now
        result = existing
    else:
        result = {
            "display_name": display_name or path.name,
            "project_path": str(path),
            "created_at": now,
            "updated_at": now
        }
        projects.insert(0, result)
    save_projects(projects)
    return result

def create_project(project_name, location):
    name = safe_folder_name(project_name)
    parent = Path(location).expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    project = parent / name
    project.mkdir(parents=True, exist_ok=True)
    (project / "history").mkdir(exist_ok=True)
    register_project(project, project_name)
    return project
