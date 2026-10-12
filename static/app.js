const $=id=>document.getElementById(id);
let project=null;
let working=false;
function busy(value){
  working=value;
  $('openFolder').disabled=value;
  $('url').disabled=value;
  $('build').disabled=value||!project;
  document.querySelectorAll('.history-select').forEach(button=>button.disabled=value||button.dataset.available==='false');
}
async function request(path,body){
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await response.json();
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Request failed. Please try again.');
  return data;
}
$('openFolder').onclick=async()=>{
  busy(true);$('status').textContent='Choose a destination, then create or select your project folder…';
  try{
    const data=await request('/api/projects/open-folder',{});
    if(data.project){
      project=data.project;
      document.title='MB Website Cloner';
      $('folderPath').textContent=project.project_path;
      $('result').hidden=true;
      $('status').textContent='Project folder ready. Enter the reference website.';
      loadHistory();
    }else $('status').textContent=project?'Folder selection cancelled. Current project kept.':'No project folder selected.';
  }catch(error){$('status').textContent=error.message;}finally{busy(false);}
};
$('buildForm').onsubmit=async event=>{
  event.preventDefault();
  if(!project)return;
  const name=project.project_name,url=$('url').value.trim();
  if(!url){$('status').textContent='Enter a reference website URL.';return;}
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
    loadHistory();
    $('status').textContent=analysis.blueprint?.rendered_browser?'Website saved. Open it below.':'Website saved using basic analysis; browser rendering was unavailable.';
  }catch(error){$('status').textContent=error.message;}finally{busy(false);}
};

async function loadHistory(){
  $('historyStatus').textContent='Loading projects…';
  try{
    const response=await fetch('/api/projects',{cache:'no-store'});
    if(!response.ok)throw Error('Could not load project history.');
    const data=await response.json();
    $('projectHistory').replaceChildren();
    for(const item of data.projects){
      const row=document.createElement('article');row.className='history-row';
      const visual=document.createElement('div');visual.className='history-preview';
      if(item.preview_url){
        const frame=document.createElement('iframe');
        frame.src=item.preview_url;
        frame.loading='lazy';
        frame.tabIndex=-1;
        frame.setAttribute('aria-hidden','true');
        visual.append(frame);
      }else{
        const fallback=document.createElement('div');
        fallback.className='history-preview-fallback';
        fallback.textContent='◇';
        visual.append(fallback);
      }
      const info=document.createElement('div');info.className='history-info';
      const title=document.createElement('h3');title.textContent=item.display_name;
      const path=document.createElement('p');path.className='history-path';path.textContent=item.project_path;
      const date=document.createElement('small');const parsed=new Date(item.updated_at);
      date.textContent=!item.available?'Folder missing or moved':item.updated_at&&!Number.isNaN(parsed.valueOf())?'Last saved: '+parsed.toLocaleString():item.has_preview?'Saved website':'Ready to build';
      info.append(title,path,date);
      const actions=document.createElement('div');actions.className='history-actions';
      const select=document.createElement('button');select.innerHTML='<span class="btn-icon">&#9654;</span> Open Project';select.className='secondary history-select';select.dataset.available=String(item.available);select.disabled=working||!item.available;
      select.onclick=()=>{
        if(working)return;
        project={project_name:item.display_name,project_path:item.project_path};
        document.title='MB Website Cloner';$('folderPath').textContent=item.project_path;
        $('url').value=item.source_url||'';$('result').hidden=true;busy(false);
        $('status').textContent='Project opened. Use Open Location to edit its files, or Build Website to regenerate.';
        $('projectTitle').scrollIntoView({behavior:'smooth'});
      };
      actions.append(select);
      if(item.preview_url){const preview=document.createElement('a');preview.className='button secondary';preview.innerHTML='<span class="btn-icon">&#128065;</span> Preview';preview.href=item.preview_url;preview.target='_blank';preview.rel='noopener';actions.append(preview);}
      const reveal=document.createElement('button');reveal.innerHTML='<span class="btn-icon">&#128193;</span> Open Location';reveal.className='secondary';reveal.disabled=!item.available;
      reveal.onclick=async()=>{try{await request('/api/projects/'+item.id+'/reveal',{});$('historyStatus').textContent='Folder opened in File Explorer.';}catch(error){$('historyStatus').textContent=error.message;}};
      actions.append(reveal);row.append(visual,info,actions);$('projectHistory').append(row);
    }
    filterHistory();
  }catch(error){$('historyStatus').textContent=error.message;}
}
function filterHistory(){
  const query=$('historySearch').value.trim().toLowerCase();
  const rows=[...document.querySelectorAll('.history-row')];
  let count=0;
  rows.forEach(row=>{const match=row.querySelector('.history-info').textContent.toLowerCase().includes(query);row.hidden=!match;if(match)count++;});
  $('historyStatus').textContent=rows.length?count+' of '+rows.length+' projects'+(count?'':' — no matches'):'No saved projects yet.';
  $('projectHistory').scrollTop=0;
}
$('historySearch').oninput=filterHistory;
$('refreshHistory').onclick=loadHistory;
loadHistory();
