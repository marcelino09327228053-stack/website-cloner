from pathlib import Path
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from analyzer import analyze_url
from builder import build_site
from project_manager import create_project, load_projects, register_project, choose_project_folder

BASE=Path(__file__).resolve().parent
GENERATED=BASE/"generated"
GENERATED.mkdir(exist_ok=True)
app=FastAPI(title="Website Reference Analyzer",version="0.1.0")
app.mount("/static",StaticFiles(directory=BASE/"static"),name="static")
app.mount("/generated",StaticFiles(directory=GENERATED,html=True),name="generated")

class AnalyzeRequest(BaseModel):
    url:str

class BuildRequest(BaseModel):
    analysis:dict
    project_path:str|None=None
    project_name:str|None=None

class CreateProjectRequest(BaseModel):
    project_name:str
    location:str

@app.get("/")
def home():
    return FileResponse(BASE/"static"/"index.html")

@app.get("/api/projects")
def projects():
    return {"projects": load_projects()}

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
    return hashlib.sha256(str(Path(path).resolve()).casefold().encode()).hexdigest()[:24]


@app.get("/api/preview/{project_id}/{asset_path:path}")
def preview_asset(project_id: str, asset_path: str):
    entry = next((item for item in load_projects() if preview_id(item["project_path"]) == project_id), None)
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
