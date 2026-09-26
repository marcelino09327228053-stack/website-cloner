let activeProjectPath="";
let activeProjectName="";
const projectName=document.getElementById("projectName");
const projectLocation=document.getElementById("projectLocation");
const createProject=document.getElementById("createProject");
const refreshProjects=document.getElementById("refreshProjects");
const recentProjects=document.getElementById("recentProjects");
const activeProject=document.getElementById("activeProject");
const activeProjectBadge=document.getElementById("activeProjectBadge");

function setActiveProject(name,path){
  activeProjectName=name||"Website Project";
  activeProjectPath=path||"";
  activeProjectBadge.textContent=activeProjectPath?"Active: "+activeProjectName:"No active project";
  activeProject.classList.toggle("hidden",!activeProjectPath);
  activeProject.textContent=activeProjectPath?(activeProjectName+" — "+activeProjectPath):"";
}

async function loadProjects(){
  try{
    const r=await fetch("/api/projects");
    const data=await r.json();
    if(!r.ok)throw Error(data.detail||"Could not load projects");
    recentProjects.replaceChildren();
    const items=data.projects||[];
    if(!items.length){
      const empty=document.createElement("p"); empty.className="muted"; empty.textContent="No saved projects yet."; recentProjects.appendChild(empty); return;
    }
    items.forEach(item=>{
      const row=document.createElement("div"); row.className="project-row";
      const info=document.createElement("div");
      const title=document.createElement("strong"); title.textContent=item.display_name||"Website Project";
      const path=document.createElement("small"); path.textContent=item.project_path||"";
      info.append(title,path);
      const open=document.createElement("button"); open.type="button"; open.className="secondary"; open.textContent="Open";
      open.onclick=()=>setActiveProject(item.display_name,item.project_path);
      row.append(info,open); recentProjects.appendChild(row);
    });
  }catch(error){ recentProjects.textContent=error.message; }
}

if(createProject)createProject.onclick=async()=>{
  const name=projectName.value.trim(), location=projectLocation.value.trim();
  if(!name||!location){status.textContent="Enter a project name and project location first.";return;}
  createProject.disabled=true; status.textContent="Creating project...";
  try{
    const r=await fetch("/api/projects/create",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({project_name:name,location})});
    const data=await r.json(); if(!r.ok)throw Error(data.detail||"Project creation failed");
    setActiveProject(data.project_name,data.project_path); status.textContent="Project ready: "+data.project_path; await loadProjects();
  }catch(error){status.textContent=error.message;}finally{createProject.disabled=false;}
};
if(refreshProjects)refreshProjects.onclick=loadProjects;
loadProjects();

const url=document.getElementById("url");
const button=document.getElementById("analyze");
const status=document.getElementById("status");
const output=document.getElementById("output");

function esc(value){
  return String(value??"").replace(/[&<>"']/g,c=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}

function list(items,empty="None detected"){
  return items?.length
    ? `<ul>${items.map(x=>`<li>${esc(typeof x==="string"?x:JSON.stringify(x))}</li>`).join("")}</ul>`
    : `<p class="muted">${empty}</p>`;
}

function render(data){
  const site=data.site||{}, blueprint=data.blueprint||{}, structure=data.structure||{}, resources=data.resources||{}, design=data.design||{};
  const designPage=design.page||{}, designRoot=design.root||{}, viewport=design.viewport||{}, designElements=design.elements||[];
  const sections=(structure.sections||[]).slice(0,30);
  const nav=(data.navigation||[]).slice(0,30);
  const forms=(structure.forms||[]).slice(0,12);
  output.innerHTML=`
    <section class="summary-card"><div class="section-head"><div><h2>${esc(site.title||site.domain||"Website")}</h2><p>${esc(site.description||"No meta description detected.")}</p></div><button id="buildSite">Build Website</button></div><div class="meta"><span>${esc(site.domain||"")}</span><span>HTTP ${esc(data.status_code)}</span></div><p id="buildStatus" class="muted"></p></section>
    <div class="grid">
      <section class="card"><h3>Blueprint</h3><h4>Section order</h4>${list(blueprint.section_order)}<h4>Interactions</h4>${list(blueprint.interactions)}<h4>Technologies</h4>${list(blueprint.technologies)}</section>
      <section class="card"><h3>Page content</h3><p><strong>${(structure.headings||[]).length}</strong> headings</p><p><strong>${sections.length}</strong> structural sections</p><p><strong>${forms.length}</strong> forms</p><p><strong>${(structure.buttons||[]).length}</strong> buttons</p></section>
      <section class="card"><h3>Assets</h3><p><strong>${(resources.images||[]).length}</strong> images</p><p><strong>${(resources.stylesheets||[]).length}</strong> stylesheets</p><p><strong>${(resources.scripts||[]).length}</strong> scripts</p></section>
      <section class="card"><h3>Visual Profile</h3><p><strong>Browser rendered:</strong> ${blueprint.rendered_browser?"Yes":"No"}</p><p><strong>Viewport:</strong> ${esc(viewport.width||"?")} × ${esc(viewport.height||"?")}</p><p><strong>Font:</strong> ${esc(designPage.fontFamily||"Not detected")}</p><p><strong>Background:</strong> ${esc(designRoot.background||designPage.background||designPage.Background||"Not detected")}</p><p><strong>Text color:</strong> ${esc(designPage.color||"Not detected")}</p><p><strong>${designElements.length}</strong> visual samples</p></section>
    </div>
    <section class="card wide"><div class="section-head"><h3>Rebuild Plan</h3><button id="copyPrompt" class="secondary">Copy Rebuild Prompt</button></div>${list(blueprint.rebuild_plan,"No rebuild plan generated.")}</section><section class="card wide"><h3>Detected sections</h3>${sections.length?sections.map(s=>`<div class="row"><span class="pill">${esc(s.type)}</span><strong>${esc(s.tag)}</strong><span>${esc(s.preview)}</span></div>`).join(""):`<p class="muted">No semantic sections detected.</p>`}</section>
    <section class="card wide"><h3>Navigation</h3>${nav.length?nav.map(n=>`<div class="row"><strong>${esc(n.text)}</strong><span>${esc(n.href)}</span></div>`).join(""):`<p class="muted">No navigation links detected.</p>`}</section>
    <section class="card wide"><h3>Forms</h3>${forms.length?forms.map((f,i)=>`<div class="row"><strong>Form ${i+1} - ${esc(f.method)}</strong><span>${esc(f.action)}</span><small>${esc((f.fields||[]).map(x=>x.name||x.type||x.tag).filter(Boolean).join(", "))}</small></div>`).join(""):`<p class="muted">No forms detected.</p>`}</section>
    <details class="card wide"><summary>Raw analysis JSON</summary><pre>${esc(JSON.stringify(data,null,2))}</pre></details>`;
  const buildButton=document.getElementById("buildSite");
  const buildStatus=document.getElementById("buildStatus");
  if(buildButton){
    buildButton.onclick=async()=>{
      if(!activeProjectPath){buildStatus.textContent="Create or open a project first.";return;}
      buildButton.disabled=true;
      buildStatus.textContent="Building website...";
      try{
        const response=await fetch("/api/build",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({analysis:data,project_path:activeProjectPath||null,project_name:activeProjectName||null})});
        const result=await response.json();
        if(!response.ok)throw Error(result.detail||"Build failed");
        buildStatus.textContent="Created: "+result.project_path;
        window.open(result.preview_url,"_blank","noopener");
      }catch(error){
        buildStatus.textContent=error.message;
      }finally{
        buildButton.disabled=false;
      }
    };
  }

  const copy=document.getElementById("copyPrompt");
  if(copy){
    copy.onclick=async()=>{
      const prompt=["Build an original website inspired by this public reference analysis.","Reference: "+(data.final_url||data.requested_url||""),"Do not copy proprietary source code, branding, or copyrighted copy verbatim.","",...(blueprint.rebuild_plan||[])].join("\\n");
      await navigator.clipboard.writeText(prompt);
      copy.textContent="Copied";
      setTimeout(()=>copy.textContent="Copy Rebuild Prompt",1200);
    };
  }
}

button.onclick=async()=>{
  const value=url.value.trim();
  if(!value)return;
  button.disabled=true;
  status.textContent="Analyzing public website...";
  output.innerHTML="";
  try{
    const r=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:value})});
    const data=await r.json();
    if(!r.ok)throw Error(data.detail||"Analysis failed");
    render(data);
    status.textContent="Analysis complete.";
  }catch(e){
    status.textContent=e.message;
    output.innerHTML=`<section class="card error">${esc(e.message)}</section>`;
  }finally{
    button.disabled=false;
  }
};

url.addEventListener("keydown",e=>{if(e.key==="Enter")button.click();});
