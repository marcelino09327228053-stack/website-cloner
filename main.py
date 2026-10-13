from pathlib import Path
import hashlib
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from analyzer import analyze_url
from builder import build_site
from template_selection import template_blueprint
from project_manager import create_project, load_projects, register_project, choose_project_folder, project_history, rename_project, delete_project, path_id, PROJECT_LOCK

BASE=Path(__file__).resolve().parent
GENERATED=BASE/"generated"
GENERATED.mkdir(exist_ok=True)
app=FastAPI(title="Website Reference Analyzer",version="0.1.0")
app.mount("/static",StaticFiles(directory=BASE/"static"),name="static")
app.mount("/generated",StaticFiles(directory=GENERATED,html=True),name="generated")


@app.middleware("http")
async def prevent_stale_app(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith(("/static/", "/api/preview/")):
        response.headers["Cache-Control"] = "no-store"
    return response

class AnalyzeRequest(BaseModel):
    url:str

class BuildRequest(BaseModel):
    analysis:dict
    project_path:str|None=None
    project_name:str|None=None

class CreateProjectRequest(BaseModel):
    project_name:str
    location:str

class RenameRequest(BaseModel):
    name: str

class DeleteRequest(BaseModel):
    mode: str
    confirmed_path: str
    confirmed: bool = False

@app.post('/api/projects/{project_id}/rename')
def rename_saved_project(project_id: str, request: RenameRequest):
    try:
        item = rename_project(project_id, request.name)
        return {'project':item, 'preview_url':'/api/preview/'+item['project_id']+'/index.html'}
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

@app.post('/api/projects/{project_id}/delete')
def delete_saved_project(project_id: str, request: DeleteRequest):
    try:
        delete_project(project_id, request.mode, request.confirmed_path, request.confirmed)
        return {'removed':True}
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

@app.get("/")
def home():
    html = (BASE/"static"/"index.html").read_text(encoding="utf-8")
    for name in ("app.js", "style.css"):
        version = hashlib.sha256((BASE/"static"/name).read_bytes()).hexdigest()[:16]
        html = html.replace(f'/static/{name}', f'/static/{name}?v={version}')
    return HTMLResponse(html)

@app.get("/api/projects")
def projects():
    return {"projects": [{**item, 'id': preview_id(item['project_path']),
                          'preview_url': '/api/preview/'+preview_id(item['project_path'])+'/index.html' if item['has_preview'] else None}
                         for item in project_history()]}


@app.post('/api/projects/{project_id}/reveal')
def reveal_project(project_id: str):
    entry = next((item for item in project_history() if preview_id(item['project_path']) == project_id), None)
    if not entry or not entry['available']:
        raise HTTPException(status_code=404, detail='Project folder is missing or has been moved. Use Open Folder to locate it.')
    try:
        os.startfile(entry['project_path'])
    except OSError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {'opened': True}

@app.post("/api/projects/create")
def create_new_project(request:CreateProjectRequest):
    try:
        project = create_project(request.project_name.strip(), request.location.strip())
        return {"project_name": request.project_name.strip(), "project_path": str(project)}
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

@app.post("/api/analyze")
async def analyze(request:AnalyzeRequest):
    try:
        preset = template_blueprint(request.url)
        if preset:
            return preset
        return await analyze_url(request.url.strip())
    except Exception as error:
        raise HTTPException(status_code=400,detail=str(error)) from error

@app.post("/api/projects/open-folder")
def open_folder():
    try:
        return {"project": choose_project_folder()}
    except Exception as error:
        raise HTTPException(status_code=400, detail="Could not open folder picker: " + str(error)) from error


def preview_id(path):
    resolved = str(Path(path).resolve()).casefold()
    entry = next((item for item in project_history() if str(item['project_path']).casefold() == resolved), None)
    return entry['project_id'] if entry else path_id(path)


@app.get("/api/preview/{project_id}/{asset_path:path}")
def preview_asset(project_id: str, asset_path: str):
    entry = next((item for item in project_history() if preview_id(item["project_path"]) == project_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Project not found")
    project = Path(entry["project_path"]).resolve()
    asset = (project / asset_path).resolve()
    if not asset.is_relative_to(project) or asset.suffix.lower() not in {".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"} or not asset.is_file():
        raise HTTPException(status_code=404, detail="Preview file not found")
    return FileResponse(asset)
@app.get("/api/project-preview")
def project_preview(path:str):
    project = Path(path).expanduser().resolve()
    index = project / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Project preview not found")
    return FileResponse(index)

@app.post("/api/build")
def build(request:BuildRequest):
    try:
        result=build_site(request.analysis, request.project_path, request.project_name)
        register_project(result["project_path"], request.project_name or result["project_name"])
        if request.project_path:
            result["preview_url"]="/api/preview/"+preview_id(result["project_path"])+"/index.html"
        else:
            result["preview_url"]="/generated/"+result["project_name"]+"/index.html"
        return result
    except Exception as error:
        raise HTTPException(status_code=400,detail=str(error)) from error
