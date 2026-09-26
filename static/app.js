const $=id=>document.getElementById(id);
let project=null;
function busy(value){
  $('openFolder').disabled=value;
  $('projectName').disabled=value||!project;
  $('url').disabled=value;
  $('build').disabled=value||!project;
}
async function request(path,body){
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await response.json();
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Request failed. Please try again.');
  return data;
}
$('openFolder').onclick=async()=>{
  busy(true);$('status').textContent='Choose a project folder in the folder dialog…';
  try{
    const data=await request('/api/projects/open-folder',{});
    if(data.project){
      project=data.project;
      $('projectName').value=project.project_name;
      $('projectTitle').textContent=project.project_name;
      document.title=project.project_name+' — Website Cloner';
      $('folderPath').textContent=project.project_path;
      $('result').hidden=true;
      $('status').textContent='Project ready. Enter a reference website.';
    }else $('status').textContent=project?'Folder selection cancelled. Current project kept.':'No folder selected.';
  }catch(error){$('status').textContent=error.message;}finally{busy(false);}
};
$('projectName').oninput=()=>{
  const name=$('projectName').value.trim();
  $('projectTitle').textContent=name||project.project_name;
  document.title=(name||project.project_name)+' — Website Cloner';
  $('result').hidden=true;
};
$('buildForm').onsubmit=async event=>{
  event.preventDefault();
  if(!project)return;
  const name=$('projectName').value.trim(),url=$('url').value.trim();
  if(!name||!url){$('status').textContent='Enter a project name and reference URL.';return;}
  busy(true);$('result').hidden=true;
  $('status').textContent='Analyzing desktop, tablet, and mobile layouts. This may take a minute…';
  try{
    const analysis=await request('/api/analyze',{url});
    $('status').textContent='Building '+name+'…';
    const result=await request('/api/build',{analysis,project_path:project.project_path,project_name:name});
    project.project_name=name;
    $('resultTitle').textContent=name;
    $('savedPath').textContent='Saved in '+result.project_path;
    $('preview').href=result.preview_url;
    $('analysis').textContent=JSON.stringify(analysis,null,2);
    $('result').hidden=false;
    $('status').textContent=analysis.blueprint?.rendered_browser?'Website saved. Open it below.':'Website saved using basic analysis; browser rendering was unavailable.';
  }catch(error){$('status').textContent=error.message;}finally{busy(false);}
};
