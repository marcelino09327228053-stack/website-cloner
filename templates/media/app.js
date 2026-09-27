const items=JSON.parse(document.getElementById('mediaData').textContent);
const $=id=>document.getElementById(id);
let category='All',view='all',saved=new Set();
try{saved=new Set(JSON.parse(localStorage.getItem('frame-saved:'+location.pathname)||'[]'));}catch{}
const categories=['All',...new Set(items.map(x=>x.category))];
const initials=name=>name.split(' ').map(x=>x[0]).slice(0,2).join('');
function element(tag,cls,text){const e=document.createElement(tag);e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function image(src,alt){const img=element('img','');img.alt=alt;img.loading='lazy';if(src)img.src=src;img.onerror=()=>{img.removeAttribute('src');img.hidden=true;};return img;}
function setCategory(value){category=value;view='all';render();}
categories.forEach(value=>{const b=element('button','chip',value);b.onclick=()=>setCategory(value);$('categories').append(b);});
categories.slice(1).forEach(value=>{const b=element('button','nav-item');b.append(element('span','interest-dot'),document.createTextNode(value));b.onclick=()=>{setCategory(value);closeSidebar();};$('interestNav').append(b);});
function popularity(item){return parseFloat(item.views)*(item.views.includes('M')?1000000:item.views.includes('K')?1000:1)||0;}
function render(){
 const query=$('search').value.trim().toLowerCase();
 let visible=items.filter(item=>(category==='All'||item.category===category)&&(view!=='saved'||saved.has(item.id))&&(`${item.title} ${item.channel}`).toLowerCase().includes(query));
 if($('sort').value==='popular'||view==='trending')visible.sort((a,b)=>popularity(b)-popularity(a));
 $('videoGrid').replaceChildren();
 for(const item of visible){
  const card=element('article','video-card'),thumb=element('button','thumbnail');thumb.setAttribute('aria-label','Open '+item.title);thumb.append(image(item.thumbnail,''));if(item.duration)thumb.append(element('span','duration',item.duration));thumb.onclick=()=>openDetails(item);
  const info=element('div','card-info'),copy=element('div',''),title=element('button','card-title',item.title);title.onclick=()=>openDetails(item);copy.append(title,element('p','channel',item.channel),element('p','video-meta',[item.views,item.age].filter(Boolean).join(' · ')));
  const save=element('button','save',saved.has(item.id)?'♥':'+');save.setAttribute('aria-label',(saved.has(item.id)?'Remove from':'Add to')+' Watch later: '+item.title);save.setAttribute('aria-pressed',String(saved.has(item.id)));save.onclick=()=>{saved.has(item.id)?saved.delete(item.id):saved.add(item.id);try{localStorage.setItem('frame-saved:'+location.pathname,JSON.stringify([...saved]));}catch{}render();};
  info.append(element('span','avatar',initials(item.channel)),copy,save);card.append(thumb,info);$('videoGrid').append(card);
 }
 $('resultCount').textContent=visible.length+' videos · Independent voices, fresh perspectives';$('empty').hidden=visible.length>0;$('savedCount').textContent=saved.size;
 $('feedTitle').textContent=view==='saved'?'Your watchlist':view==='trending'?'Trending in the collection':'For your curiosity';
 document.querySelectorAll('.chip').forEach(b=>{b.classList.toggle('active',b.textContent===category);b.setAttribute('aria-pressed',String(b.textContent===category));});
 document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===view);b.setAttribute('aria-current',b.dataset.view===view?'page':'false');});
}
let lastTrigger=null;
function openDetails(item){lastTrigger=document.activeElement;$('player').replaceChildren();if(item.video){const v=element('video','');v.controls=true;v.src=item.video;v.poster=item.thumbnail;$('player').append(v);}else $('player').append(image(item.thumbnail,''));$('detailTitle').textContent=item.title;$('detailCategory').textContent=item.category;$('detailMeta').textContent=[item.channel,item.views,item.age].filter(Boolean).join(' · ');$('detailNote').textContent=item.video?'Enjoy the film.':'Demo preview — connect a video source to enable playback.';$('details').showModal();}
$('closeDetails').onclick=()=>$('details').close();$('details').addEventListener('click',event=>{if(event.target===$('details'))$('details').close();});$('details').addEventListener('close',()=>{$('player').querySelector('video')?.pause();lastTrigger?.focus();});
if(items.length){const first=items[0];$('featureImage').src=first.thumbnail;$('featureImage').onerror=()=>$('featureImage').hidden=true;$('featureTitle').textContent=first.title;$('featureCategory').textContent=first.category+' / '+first.channel;$('featureMeta').textContent=[first.duration,first.views].filter(Boolean).join(' · ');$('watchFeatured').onclick=()=>openDetails(first);}
$('search').oninput=render;document.querySelector('.search').onsubmit=event=>{event.preventDefault();render();};$('sort').onchange=render;$('resetFilters').onclick=()=>{category='All';view='all';$('search').value='';render();};
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{view=b.dataset.view;category='All';$('search').value='';render();closeSidebar();});
const toggle=document.querySelector('.menu-toggle'),scrim=document.querySelector('.scrim');
function closeSidebar(){$('sidebar').classList.remove('open');$('sidebar').inert=innerWidth<=850;scrim.hidden=true;toggle.setAttribute('aria-expanded','false');}
toggle.onclick=()=>{const open=$('sidebar').classList.toggle('open');$('sidebar').inert=!open;scrim.hidden=!open;toggle.setAttribute('aria-expanded',String(open));};scrim.onclick=closeSidebar;
document.addEventListener('keydown',event=>{if(event.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)&&!$('details').open){event.preventDefault();$('search').focus();}if(event.key==='Escape'){closeSidebar();}});
matchMedia('(min-width:851px)').addEventListener('change',closeSidebar);
closeSidebar();
render();
