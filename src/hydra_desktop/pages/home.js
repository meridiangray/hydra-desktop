const BOOT=JSON.parse(document.getElementById('boot').textContent);
const token=BOOT.token;
const error=document.getElementById('error');
const welcome=document.getElementById('welcome');
const loading=document.getElementById('loading');
const ring=document.getElementById('loader-ring');
const percent=document.getElementById('loading-percent');
let opening=false;
let selecting=false;
async function request(action,data) {
    const response=await fetch('/_desktop/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-Hydra-Token':token},body:JSON.stringify(data)});
    const result=await response.json();
    if (!response.ok) throw result;
    return result;
}
let shown=0;
function setLoadingProgress({stage,fraction}) {
    if (typeof stage==='string') document.getElementById('loading-stage').textContent=stage;
    if (typeof fraction==='number' && Number.isFinite(fraction)) shown=Math.max(shown,Math.min(1,Math.max(0,fraction)));
    const pct=Math.round(shown*100);
    document.getElementById('loading-fill').style.width=pct+'%';
    document.querySelector('.loader-track').setAttribute('aria-valuenow',pct);
    percent.textContent=pct+'%';
}
function showLoading(path,build) {
    document.getElementById('loading-title').textContent=build?'Building archive':'Opening archive';
    shown=0;
    setLoadingProgress({stage:build?'Preparing to build':'Preparing',fraction:0});
    document.getElementById('loading-name').textContent=path.replaceAll(String.fromCharCode(92),'/').split('/').pop();
    welcome.inert=true;
    welcome.setAttribute('aria-busy','true');
    loading.hidden=false;
    return performance.now();
}
function hideLoading() {
    loading.hidden=true;
    welcome.inert=false;
    welcome.removeAttribute('aria-busy');
}
async function openArchive(path,rebuild=false) {
    if (!path || opening) return;
    opening=true;
    error.textContent='';
    async function attempt(build) {
        const started=showLoading(path,build);
        let watching=true;
        let timer;
        async function poll() {
            try {
                const response=await fetch('/_desktop/progress',{headers:{'X-Hydra-Token':token},cache:'no-store'});
                if (response.ok) {
                    const status=await response.json();
                    if (watching) setLoadingProgress(status);
                }
            } catch (error) { /* Opening can finish even if a status poll fails. */ }
            if (watching) timer=setTimeout(poll,250);
        }
        timer=setTimeout(poll,100);
        try {
            const opened=await request('open',{path,build});
            watching=false;
            clearTimeout(timer);
            setLoadingProgress({stage:'Ready',fraction:1});
            await new Promise(resolve=>setTimeout(resolve,Math.max(0,300-(performance.now()-started))));
            location.assign(opened.start||'/');
        } finally {
            watching=false;
            clearTimeout(timer);
        }
    }
    try {
        await attempt(rebuild);
    } catch (result) {
        hideLoading();
        if (result.requires_build) {
            if (confirm(result.error+' This will update files in the selected folder.')) {
                try { await attempt(true); }
                catch (failure) { hideLoading(); error.textContent=failure.error||String(failure); }
            }
        } else error.textContent=result.error||String(result);
    } finally {
        opening=false;
    }
}
const wizlane=document.getElementById('wizard');
const newbtn=document.getElementById('newproj');
newbtn.onclick=()=>{
    wizlane.hidden=!wizlane.hidden;
    newbtn.classList.toggle('on',!wizlane.hidden);
    newbtn.setAttribute('aria-expanded',String(!wizlane.hidden));
    if (!wizlane.hidden) document.getElementById('pname').focus();
};
for (const kind of ['pack','folder']) {
    document.getElementById(kind).onclick=async () => {
        if (selecting || opening) return;
        selecting=true;
        try {
            const chosen=await request('pick',{kind:kind==='pack'?'file':'folder'});
            await openArchive(chosen.path);
        } catch (failure) { error.textContent=failure.error||String(failure); }
        finally { selecting=false; }
    };
}
document.querySelectorAll('.recent').forEach(button=>button.onclick=()=>openArchive(button.dataset.path));
{const want=new URLSearchParams(location.search).get('pick');   /* the window bar's Archives menu: open a file or a folder here, with this page's picker and load bar */
if (want==='file'||want==='folder') { history.replaceState(null,'','/_desktop/'); document.getElementById(want==='file'?'pack':'folder').click(); }}

/* ---- the new-project wizard ---- */
const stepsEls=[...document.querySelectorAll('.step')];
const dots=[...document.querySelectorAll('#steps i')];
const wback=document.getElementById('wback'), wnext=document.getElementById('wnext'), wcreate=document.getElementById('wcreate');
const created=document.getElementById('created');
const wiz={step:0,sources:[]};
function picked(name){const el=document.querySelector(`input[name=${name}]:checked`);return el?el.value:''}
function showStep(i) {
    wiz.step=i;
    stepsEls.forEach((s,j)=>s.hidden=j!==i);
    dots.forEach((d,j)=>d.classList.toggle('on',j<=i));
    wback.disabled=i===0;
    wnext.hidden=i===stepsEls.length-1;
    wcreate.hidden=i!==stepsEls.length-1;
}
function drawDocs() {
    const box=document.getElementById('docs');
    box.innerHTML='';
    wiz.sources.forEach((p,i)=>{
        const chip=document.createElement('span');
        chip.append(p.replaceAll(String.fromCharCode(92),'/').split('/').pop());
        const x=document.createElement('button');
        x.type='button';x.textContent='×';x.title='Remove';
        x.onclick=()=>{wiz.sources.splice(i,1);drawDocs()};
        chip.append(x);box.append(chip);
    });
}
wnext.onclick=()=>{
    created.textContent='';
    if (wiz.step===2 && !document.getElementById('pfolder').value.trim()) {created.textContent='Choose a folder for the project.';return}
    showStep(wiz.step+1);
};
wback.onclick=()=>showStep(Math.max(0,wiz.step-1));
document.getElementById('browse').onclick=async()=>{
    if (selecting) return; selecting=true;
    try {
        const chosen=await request('pick',{kind:'newfolder'});
        if (chosen.path) {
            const f=document.getElementById('pfolder');
            const name=document.getElementById('pname').value.trim();
            f.value=(chosen.path.endsWith('/')||chosen.path.endsWith('\\'))&&name?chosen.path+name
                  :chosen.path.replace(/[\\/]+$/,'')+(name?'/'+name:'');
        }
    } catch (failure) { created.textContent=failure.error||String(failure); }
    finally { selecting=false; }
};
document.getElementById('adddocs').onclick=async()=>{
    if (selecting) return; selecting=true;
    try {
        const chosen=await request('pick',{kind:'documents'});
        for (const p of chosen.paths||[]) if (!wiz.sources.includes(p)) wiz.sources.push(p);
        drawDocs();
    } catch (failure) { created.textContent=failure.error||String(failure); }
    finally { selecting=false; }
};
wcreate.onclick=async()=>{
    if (opening) return;
    opening=true;created.textContent='';
    const path=document.getElementById('pfolder').value.trim();
    const name=document.getElementById('pname').value.trim()
        || path.replaceAll(String.fromCharCode(92),'/').replace(/[/]+$/,'').split('/').pop();
    const started=showLoading(path,false);
    document.getElementById('loading-title').textContent='Creating project';
    try {
        const result=await request('new',{path,name,view:picked('view'),theme:picked('theme'),sources:wiz.sources});
        if (result.empty) {
            hideLoading();
            created.textContent='Created. Add sources, then open it from Recent archives.';
            setTimeout(()=>location.reload(),1600);
            return;
        }
        setLoadingProgress({stage:'Ready',fraction:1});
        await new Promise(resolve=>setTimeout(resolve,Math.max(0,300-(performance.now()-started))));
        location.assign(result.start||'/');
    } catch (failure) {
        hideLoading();
        created.textContent=failure.error||String(failure);
    } finally {
        opening=false;
    }
};
showStep(0);
if (BOOT.auto_open) openArchive(BOOT.auto_open,true);
