const BOOT=JSON.parse(document.getElementById('boot').textContent), TOKEN=BOOT.token, KEY='hydra.profile.draft';
const $=id=>document.getElementById(id);
const I=b=>`<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${b}</svg>`;
const ICON={
 text:'<path d="M4 7h16M4 12h16M4 17h10"/>',
 link:'<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
 website:'<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20M2 12h20"/>',
 email:'<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
 x:'<path d="M4 4h4l12 16h-4zM4 20l7-8M20 4l-7 8"/>',
 github:'<path d="m8 8-5 4 5 4M16 8l5 4-5 4M14 5l-4 14"/>',
 linkedin:'<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 11v5M8 8v.01M12 16v-5M12 13a2.5 2.5 0 0 1 5 0v3"/>',
 mastodon:'<circle cx="12" cy="12" r="4"/><path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8"/>',
 bluesky:'<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>',
 youtube:'<path d="M2.5 17a24.1 24.1 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.6 49.6 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24.1 24.1 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.6 49.6 0 0 1-16.2 0A2 2 0 0 1 2.5 17"/><path d="m10 15 5-3-5-3z"/>',
 instagram:'<rect width="20" height="20" x="2" y="2" rx="5"/><circle cx="12" cy="12" r="4"/><path d="M17.5 6.5h.01"/>',
 plus:'<path d="M12 5v14M5 12h14"/>', close:'<path d="M18 6 6 18M6 6l12 12"/>',
 dice:'<rect width="18" height="18" x="3" y="3" rx="3"/><path d="M8 8h.01M16 8h.01M12 12h.01M8 16h.01M16 16h.01"/>',
};
const NAMES={text:'Text',link:'Link',website:'Website',email:'Email',x:'X',github:'GitHub',linkedin:'LinkedIn',mastodon:'Mastodon',bluesky:'Bluesky',youtube:'YouTube',instagram:'Instagram'};
const SOCIAL=new Set(['x','github','linkedin','mastodon','bluesky','youtube','instagram']);
const detect=v=>{v=(v||'').trim();
 if(/^https?:\/\/\S+$/i.test(v)){const h=v.split('//')[1].split('/')[0].toLowerCase().replace(/^www\./,'');
  for(const [k,hs] of Object.entries(BOOT.hosts))if(hs.some(x=>h===x||h.endsWith('.'+x)))return k;return 'website'}
 if(/^@[\w.-]+@[\w-]+(\.[\w-]+)+$/.test(v))return 'mastodon';
 if(/^@[\w-]+(\.[\w-]+)*\.bsky\.social$/.test(v))return 'bluesky';
 if(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v))return 'email';
 return 'text'};
const hue=s=>{let h=0;for(const c of s)h=(h*31+c.charCodeAt(0))%360;return h};
const initials=(name,code)=>(name||code).split(/\s+/).filter(Boolean).slice(0,2).map(w=>w[0]).join('').toUpperCase();
let saved=BOOT.profile, st=JSON.parse(JSON.stringify(saved));
st.fields.forEach(f=>f.auto=detect(f.value)===f.kind||f.kind==='text');
try{const d=JSON.parse(localStorage.getItem(KEY)||'null');if(d&&d.codename===saved.codename)st=d}catch(e){}
const snap=()=>JSON.stringify({name:st.name,handle:st.handle,bio:st.bio,portrait:st.portrait,badges:saved.badges,fields:st.fields.map(f=>({label:f.label,value:f.value,kind:f.kind}))});
const clean=()=>JSON.stringify({name:saved.name,handle:saved.handle,bio:saved.bio,portrait:saved.portrait,badges:saved.badges,fields:saved.fields.map(f=>({label:f.label,value:f.value,kind:f.kind}))});
const dirty=()=>{$('save').disabled=snap()===clean();try{if($('save').disabled)localStorage.removeItem(KEY);else localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}};
const paint=()=>{
 const p=$('portrait');p.className=st.portrait?'has':'';p.style.background=st.portrait?'':`hsl(${hue(st.codename)} 32% 38%)`;
 p.innerHTML=st.portrait?`<img alt="" src="/_desktop/profile/${st.portrait}"><span class="rm" role="button" aria-label="Remove" title="Remove">${I(ICON.close)}</span>`:initials(st.name,st.codename);
 $('name').placeholder=st.codename;$('code').textContent=st.codename;
};
const rows=()=>{
 const box=$('fields');box.innerHTML='';
 st.fields.forEach((f,i)=>{
  const r=document.createElement('div');r.className='frow';
  const ic=document.createElement('button');ic.type='button';ic.className='ib';ic.setAttribute('aria-label',NAMES[f.kind]);ic.setAttribute('aria-haspopup','menu');ic.title=NAMES[f.kind];ic.innerHTML=I(ICON[f.kind]);
  const l=document.createElement('input');l.className='l';l.value=f.label;l.maxLength=BOOT.limits.label;l.placeholder='Site';l.setAttribute('aria-label','Label');
  const v=document.createElement('input');v.className='v';v.value=f.value;v.maxLength=BOOT.limits.value;v.placeholder='https://example.org';v.setAttribute('aria-label','Value');
  const x=document.createElement('button');x.type='button';x.className='ib ghost x';x.setAttribute('aria-label','Remove');x.title='Remove';x.innerHTML=I(ICON.close);
  const setKind=k=>{f.kind=k;ic.innerHTML=I(ICON[k]);ic.title=NAMES[k];ic.setAttribute('aria-label',NAMES[k])};
  l.oninput=()=>{f.label=l.value;dirty()};
  v.oninput=()=>{f.value=v.value;if(f.auto){const k=detect(v.value);setKind(k);if(!f.label&&k!=='text'){f.label=NAMES[k];l.value=f.label}}dirty()};
  x.onclick=()=>{st.fields.splice(i,1);rows();dirty()};
  ic.onclick=e=>{e.stopPropagation();const open=r.querySelector('.menu');closeMenus();if(open)return;ic.setAttribute('aria-expanded','true');
   const m=document.createElement('div');m.className='menu';m.setAttribute('role','menu');
   for(const k of BOOT.kinds){const b=document.createElement('button');b.type='button';b.setAttribute('role','menuitemradio');b.setAttribute('aria-checked',k===f.kind);b.innerHTML=I(ICON[k])+NAMES[k];
    b.onclick=ev=>{ev.stopPropagation();f.auto=false;setKind(k);closeMenus();dirty()};m.append(b)}
   r.append(m)};
  r.append(ic,l,v,x);box.append(r)});
 $('add').disabled=st.fields.length>=BOOT.limits.fields;
};
const closeMenus=()=>document.querySelectorAll('.menu').forEach(m=>{m.parentNode.querySelector('.ib').removeAttribute('aria-expanded');m.remove()});
document.addEventListener('click',closeMenus);document.addEventListener('keydown',e=>{if(e.key!=='Escape')return;if(document.querySelector('.menu')){closeMenus();return}e.preventDefault();if(history.length>1)history.back();else location.href='/'});
$('add').innerHTML=I(ICON.plus)+'Field';$('reroll').innerHTML=I(ICON.dice);
$('add').onclick=()=>{st.fields.push({label:'',value:'',kind:'text',auto:true});rows();dirty();$('fields').lastChild.querySelector('.l').focus()};
for(const k of ['name','bio'])$(k).oninput=e=>{st[k]=e.target.value;if(k==='name')paint();dirty()};
$('handle').oninput=e=>{st.handle=e.target.value.replace(/^@/,'');dirty()};
$('portrait').onclick=e=>{if(e.target.closest('.rm')){st.portrait='';paint();dirty();return}$('file').click()};
$('file').onchange=async()=>{const f=$('file').files[0];$('file').value='';if(!f)return;$('err').textContent='';
 try{const r=await fetch('/_desktop/profile/portrait',{method:'POST',headers:{'X-Hydra-Token':TOKEN,'Content-Type':f.type||'application/octet-stream'},body:f});
  const d=await r.json();if(!r.ok)throw new Error(d.error||r.status);st.portrait=d.portrait;paint();dirty()}catch(e){$('err').textContent=e.message}};
$('reroll').onclick=async()=>{try{const r=await fetch('/_desktop/profile/reroll',{method:'POST',headers:{'X-Hydra-Token':TOKEN,'Content-Type':'application/json'},body:'{}'});
 const d=await r.json();if(!r.ok)throw new Error(d.error);st.codename=saved.codename=d.codename;paint();dirty()}catch(e){$('err').textContent=e.message}};
$('form').onsubmit=async e=>{e.preventDefault();$('err').textContent='';$('save').disabled=true;
 try{const r=await fetch('/_desktop/profile.json',{method:'POST',headers:{'X-Hydra-Token':TOKEN,'Content-Type':'application/json'},body:snap()});
  const d=await r.json();if(!r.ok)throw new Error(d.error||r.status);
  saved=d;st=JSON.parse(JSON.stringify(d));st.fields.forEach(f=>f.auto=detect(f.value)===f.kind||f.kind==='text');
  try{localStorage.removeItem(KEY)}catch(x){}fill();dirty()}catch(x){$('err').textContent=x.message;dirty()}};
const fill=()=>{$('name').value=st.name;$('handle').value=st.handle;$('bio').value=st.bio;rows();paint()};
fill();dirty();
