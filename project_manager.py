from pathlib import Path
from datetime import datetime
import json
import subprocess
import sys
import os
import hashlib
import re
import shutil
import uuid
from threading import RLock

PROJECT_LOCK = RLock()

BASE = Path(__file__).resolve().parent
REGISTRY = BASE / "projects.json"


def choose_project_folder():
    # A separate process keeps the native dialog on its own main UI thread.
    script = '''import tkinter as tk
from tkinter import filedialog
import json
root=tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
folder=filedialog.askdirectory(title='Open project folder', parent=root)
root.destroy()
print(json.dumps(folder))
'''
    result = subprocess.run([sys.executable, "-c", script], capture_output=True,
                            text=True, check=True)
    folder = json.loads(result.stdout.strip())
    if not folder:
        return None
    path = Path(folder).resolve()
    name = path.name
    metadata = path / "project.json"
    if metadata.exists():
        try:
            saved = json.loads(metadata.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                name = saved.get("display_name") or name
        except (ValueError, OSError):
            pass  # An unrelated or damaged metadata file must not block opening a folder.
    register_project(path, name)
    return {"project_name": name, "project_path": str(path)}

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
    temporary = REGISTRY.with_suffix('.tmp')
    temporary.write_text(json.dumps(projects, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(REGISTRY)


def path_id(path):
    return hashlib.sha256(str(Path(path).resolve()).casefold().encode()).hexdigest()[:24]


def project_history():
    """Include registered folders and older builds saved under generated/."""
    entries = {str(Path(item['project_path']).resolve()).casefold(): dict(item)
               for item in load_projects() if isinstance(item, dict) and item.get('project_path')}
    for metadata in [BASE / 'project.json', *(BASE / 'generated').glob('*/project.json')]:
        if not metadata.is_file():
            continue
        key = str(metadata.parent.resolve()).casefold()
        if key not in entries:
            entries[key] = {'project_path': str(metadata.parent.resolve())}
    result = []
    for item in entries.values():
        if item.get('hidden'):
            continue
        path = Path(item['project_path']).resolve()
        try:
            data = json.loads((path / 'project.json').read_text(encoding='utf-8'))
            if not isinstance(data, dict): data = {}
        except (OSError, ValueError):
            data = {}
        result.append({**item, 'project_path': str(path),
                       'project_id': item.get('project_id') or data.get('project_id') or path_id(path),
                       'display_name': data.get('display_name') or item.get('display_name') or path.name,
                       'updated_at': data.get('updated_at') or item.get('updated_at', ''),
                       'source_url': data.get('source_url', ''),
                       'description': data.get('description', ''),
                       'available': path.is_dir(), 'has_preview': (path/'index.html').is_file()})
    return sorted(result, key=lambda item: str(item['updated_at']), reverse=True)

def register_project(project_path, display_name=None):
    path = Path(project_path).expanduser().resolve()
    now = datetime.now().isoformat(timespec="seconds")
    projects = load_projects()
    key = str(path).casefold()
    existing = next((x for x in projects if str(x.get("project_path", "")).casefold() == key), None)
    if existing:
        existing.pop('hidden', None)
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


def managed_entry(identifier):
    entry = next((item for item in project_history() if item['project_id'] == identifier), None)
    if not entry:
        raise ValueError('Project not found. Refresh history.')
    return entry


def validated_project(entry):
    raw = Path(entry['project_path']).absolute()
    path = raw.resolve()
    source = BASE.resolve()
    if path == Path(path.anchor) or path == source or source.is_relative_to(path):
        raise ValueError('The source folder and drive roots are protected.')
    if path.is_relative_to(source) and not path.is_relative_to(source/'generated'):
        raise ValueError('Website Cloner source files are protected.')
    if path == source/'generated':
        raise ValueError('The generated-project parent folder is protected.')
    for parent in (raw, *raw.parents):
        if parent.is_symlink() or parent.is_junction():
            raise ValueError('Linked folders cannot be renamed or deleted.')
    if not path.is_dir():
        raise ValueError('Project folder is missing.')
    for root, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            node = Path(root)/name
            if node.is_symlink() or node.is_junction():
                raise ValueError('Project contains a linked path; operation refused.')
    metadata = json.loads((path/'project.json').read_text(encoding='utf-8'))
    if not isinstance(metadata, dict) or Path(metadata.get('project_path', '')).resolve() != path or metadata.get('main_file') != 'index.html':
        raise ValueError('Folder is not a verified Website Cloner project.')
    return path, metadata


def rename_project(identifier, name):
    with PROJECT_LOCK:
        if not name or name != name.strip() or name.endswith(('.', ' ')) or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name in ('.', '..') or len(name) > 100:
            raise ValueError('Enter a valid folder name (1–100 characters).')
        if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
            raise ValueError('That folder name is reserved by Windows.')
        entry = managed_entry(identifier)
        path, metadata = validated_project(entry)
        destination = path.parent/name
        if destination.exists():
            raise ValueError('A folder with that name already exists.')
        if destination.resolve().parent != path.parent:
            raise ValueError('Rename must stay in the same parent folder.')
        original = (path/'project.json').read_bytes()
        records = load_projects()
        records = [x for x in records if str(x.get('project_path','')).casefold() != str(path).casefold()]
        records.append({**entry, 'project_path':str(destination), 'display_name':name,
                        'project_id':identifier, 'updated_at':datetime.now().isoformat(timespec='seconds')})
        path.rename(destination)
        try:
            metadata.update(project_path=str(destination), project_name=name, display_name=name, project_id=identifier)
            (destination/'project.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
            save_projects(records)
        except Exception:
            (destination/'project.json').write_bytes(original)
            destination.rename(path)
            raise
        return managed_entry(identifier)


def delete_project(identifier, mode, confirmed_path, confirmed):
    with PROJECT_LOCK:
        entry = managed_entry(identifier)
        if not confirmed or confirmed_path != entry['project_path']:
            raise ValueError('Confirm the exact project folder before continuing.')
        if mode not in ('history', 'files'):
            raise ValueError('Choose a delete option.')
        path = Path(entry['project_path']).resolve()
        records = load_projects()
        updated = [x for x in records if str(x.get('project_path','')).casefold() != str(path).casefold()]
        updated.append({**entry, 'hidden':True})
        if mode == 'history':
            save_projects(updated)
            return
        path, _ = validated_project(entry)
        # Quarantine the verified folder before removing files; restore it if registry persistence fails.
        staging = path.parent/('.cloner-delete-'+uuid.uuid4().hex)
        if staging.exists() or staging.resolve().parent != path.parent:
            raise ValueError('Invalid deletion staging path.')
        path.rename(staging)
        try:
            save_projects(updated)
        except Exception:
            staging.rename(path)
            raise
        try:
            shutil.rmtree(staging)
        except OSError as error:
            # Any remaining files are recoverable; report their actual location.
            raise ValueError(f'History removed, but some files could not be deleted. Remaining files: {staging}') from error

def create_project(project_name, location):
    name = safe_folder_name(project_name)
    parent = Path(location).expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    project = parent / name
    project.mkdir(parents=True, exist_ok=True)
    (project / "history").mkdir(exist_ok=True)
    register_project(project, project_name)
    return project
