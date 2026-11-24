/* The desktop window bar's extras, loaded by desktop/chrome.js from /_desktop/chrome-ext.js.
   Served from Python, so changing it needs no shell rebuild. Adds the Save button and its dialog
   (docs/plans/save.md): a summary, details, what goes in (collections with their counts and a sourced bar, records,
   review, rules, sources, files), sign; behind the menu a version tag, amending the last save, and History
   (recent saves: restore to one, tag one). Every write is a history step or asked for by name. */
(() => {
    const bar = document.getElementById('hydra-windowbar');
    if (!bar || window.__hydraSave) return;
    window.__hydraSave = true;
    const nav = bar.querySelector('.window-nav');
    if (!nav) return;

    const style = document.createElement('style');
    style.textContent = `
#hydra-windowbar .window-mark{background:#1d4f9e;border-color:#a9c3ea;color:#f4f7fd}
#hydra-windowbar .window-save{display:flex;align-self:stretch;flex:none;app-region:no-drag;-webkit-app-region:no-drag}
#hydra-windowbar .window-save[hidden]{display:none}
#hydra-windowbar .window-save button{width:34px;padding:0;justify-content:center;display:flex;align-items:center;font:inherit;position:relative}
#hydra-windowbar .window-save svg{width:17px;height:17px;stroke-width:1.1}
#hydra-windowbar .window-save[data-dirty] button{color:var(--accent,#586c50)}
#hydra-windowbar .window-save[data-dirty] button::after{content:"";position:absolute;top:calc(50% - 10px);right:5px;width:6px;height:6px;border-radius:50%;background:currentColor}
#hydra-windowbar .window-save[data-busy] button{animation:hs-pulse 1s ease-in-out infinite alternate}
@keyframes hs-pulse{to{opacity:.35}}
#hydra-windowbar .window-title{visibility:hidden}
#hydra-windowbar .window-archives{display:flex;align-items:center;justify-content:center;align-self:stretch;flex:none;width:34px;padding:0;border-radius:0}
#hydra-windowbar .window-archives svg{width:17px;height:17px;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
#hydra-windowbar .window-brand{cursor:pointer;app-region:no-drag;-webkit-app-region:no-drag}
#hydra-windowbar .window-brand:focus-visible,#hydra-windowbar .window-archives:focus-visible{outline:2px solid var(--accent,#586c50);outline-offset:-2px}
#hydra-windowbar .window-brand:hover{opacity:.8}
#hydra-windowbar .arch-menu{position:fixed;z-index:2147483640;display:flex;gap:2px;padding:3px;background:var(--panel,#fff);border:1px solid var(--line,#d6d4ce);border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.18);app-region:no-drag;-webkit-app-region:no-drag}
#hydra-windowbar .arch-menu[hidden]{display:none}
#hydra-windowbar .arch-menu button{display:grid;place-items:center;width:32px;height:30px;padding:0;border:0;border-radius:6px;background:none;color:var(--ink,#222);cursor:pointer}
#hydra-windowbar .arch-menu button:hover,#hydra-windowbar .arch-menu button:focus-visible{background:var(--tint,rgba(0,0,0,.07));color:var(--accent,#586c50);outline:none}
#hydra-windowbar .arch-menu svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
#hydra-save{--hs-r:calc(var(--radius,12px) * .6);position:fixed;inset:0;z-index:2147483640;display:flex;align-items:flex-start;justify-content:center;padding:calc(var(--windowbar-height,64px) + .25rem) 1rem 1rem;background:color-mix(in srgb,var(--ink,#242421) 26%,transparent);font:14px/1.45 var(--sans,system-ui,sans-serif);color:var(--ink,#242421)}
#hydra-save *{box-sizing:border-box}
#hydra-save .hs{position:relative;width:min(46rem,100%);max-height:100%;display:flex;flex-direction:column;background:var(--panel,#f6f5f1);border:1px solid var(--line,#d6d4ce);border-radius:var(--radius,12px);box-shadow:0 18px 48px -12px rgba(0,0,0,.32),0 2px 6px rgba(0,0,0,.08)}
#hydra-save .hs-top{display:flex;align-items:center;gap:.4rem;padding:.85rem 1rem .4rem 1.15rem}
#hydra-save h2{flex:1;margin:0;padding:0;border:0;font:400 1.3rem/1.2 var(--serif,Georgia,serif);color:var(--ink,#242421)}
#hydra-save .hs-body{flex:1;min-height:0;overflow-y:auto;padding:.35rem 1.15rem .9rem;display:flex;flex-direction:column;gap:.9rem;scrollbar-width:thin}
#hydra-save .hs-foot{display:flex;align-items:center;gap:.75rem;padding:.75rem 1.15rem;border-top:1px solid var(--line,#d6d4ce)}
#hydra-save .hs-who{color:var(--muted,#666760);font-size:.86rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#hydra-save .hs-gap{flex:1}
#hydra-save input[type=text],#hydra-save textarea{display:block;width:100%;font:inherit;font-size:.95rem;color:var(--ink,#242421);background:var(--input,var(--bg,#fff));border:1px solid var(--line,#d6d4ce);border-radius:var(--hs-r);padding:.5rem .65rem;resize:none}
#hydra-save textarea{min-height:2.6rem;field-sizing:content;max-height:9rem}
#hydra-save input[type=text]::placeholder,#hydra-save textarea::placeholder{color:var(--muted,#666760);opacity:.8}
#hydra-save input:focus-visible,#hydra-save textarea:focus-visible,#hydra-save button:focus-visible{outline:2px solid var(--link,var(--accent,#586c50));outline-offset:-1px}
#hydra-save .hs-fields{display:flex;flex-direction:column;gap:.5rem}
#hydra-save input[type=checkbox]{width:.95rem;height:.95rem;margin:0;accent-color:var(--link,var(--accent,#586c50));flex:none}
#hydra-save .btn{font:inherit;font-size:.9rem;padding:.42rem 1.05rem;border-radius:var(--hs-r);border:1px solid var(--line,#d6d4ce);background:transparent;color:inherit;cursor:pointer}
#hydra-save .btn:hover{background:var(--soft,rgba(0,0,0,.04))}
#hydra-save .btn.pri{background:var(--link,var(--accent,#586c50));border-color:var(--link,var(--accent,#586c50));color:var(--bg,#fff);font-weight:550}
#hydra-save .btn.pri:hover{filter:brightness(1.07)}
#hydra-save .btn:disabled{opacity:.45;cursor:default;filter:none}
#hydra-save .ib{display:grid;place-items:center;width:1.75rem;height:1.75rem;padding:0;border:0;border-radius:6px;background:transparent;color:var(--muted,#666760);cursor:pointer;flex:none}
#hydra-save .ib:hover{background:var(--soft,rgba(0,0,0,.05));color:var(--ink,#242421)}
#hydra-save .ib[data-armed]{color:var(--red,#b3261e);background:color-mix(in srgb,var(--red,#b3261e) 12%,transparent)}
#hydra-save .ib[aria-pressed=true]{color:var(--link,#586c50)}
#hydra-save .ib svg{width:15px;height:15px}
#hydra-save .hs-menu{position:absolute;top:2.9rem;right:.8rem;z-index:2;min-width:11rem;padding:.3rem;background:var(--panel,#f6f5f1);border:1px solid var(--line,#d6d4ce);border-radius:var(--hs-r);box-shadow:0 10px 28px -8px rgba(0,0,0,.3)}
#hydra-save .hs-menu button{display:flex;align-items:center;gap:.55rem;width:100%;padding:.42rem .6rem;border:0;border-radius:6px;background:transparent;color:inherit;font:inherit;font-size:.9rem;text-align:left;cursor:pointer}
#hydra-save .hs-menu button:hover{background:var(--soft,rgba(0,0,0,.05))}
#hydra-save .hs-menu svg{width:15px;height:15px;color:var(--muted,#666760)}
#hydra-save .grp{display:grid;grid-template-columns:1.6rem minmax(0,1fr) 5rem 5rem 4.6rem 6.6rem;align-items:stretch}
#hydra-save .grp.plain{grid-template-columns:1.6rem minmax(0,1fr) auto 2.2rem}
#hydra-save .gh>*,#hydra-save .row>*{display:flex;align-items:center;padding-right:.6rem}
#hydra-save .gh>.num,#hydra-save .row>.num{justify-content:flex-end}
#hydra-save .row>.bc{padding-left:.9rem;padding-right:0}
#hydra-save .grp.plain .row>*{padding-top:.2rem;padding-bottom:.2rem}
#hydra-save .gh{display:contents}
#hydra-save .gh>*{padding-top:0;padding-bottom:.3rem;border-bottom:1px solid var(--line,#d6d4ce);font-size:.76rem;font-weight:600;letter-spacing:.02em;color:var(--muted,#666760);align-self:end}
#hydra-save .gh h3{margin:0;font:inherit;font-size:.82rem;color:var(--ink,#242421)}
#hydra-save .num{text-align:right;font-variant-numeric:tabular-nums}
#hydra-save .row{display:contents}
#hydra-save .row>*{padding-top:.38rem;padding-bottom:.38rem;border-bottom:1px solid color-mix(in srgb,var(--line,#d6d4ce) 55%,transparent)}
#hydra-save .row:hover>*{background:color-mix(in srgb,var(--soft,#eee) 60%,transparent)}
#hydra-save .nm{display:flex;align-items:center;gap:.4rem;min-width:0;cursor:pointer}
#hydra-save .nm span.t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#hydra-save .nm .car{display:grid;place-items:center;width:12px;height:12px;flex:none;color:var(--muted,#666760);transition:transform .12s}
#hydra-save .nm .car svg{width:12px;height:12px;display:block}
#hydra-save .nm.open .car{transform:rotate(90deg)}
#hydra-save .chip{flex:none;font-size:.7rem;font-weight:600;letter-spacing:.03em;padding:.05rem .4rem;border-radius:999px;background:color-mix(in srgb,var(--link,#586c50) 14%,transparent);color:var(--link,#586c50)}
#hydra-save .chip.gone{background:color-mix(in srgb,var(--red,#b3261e) 12%,transparent);color:var(--red,#b3261e)}
#hydra-save .chip.tag{background:var(--soft,#eee);color:var(--ink,#242421);font-weight:500}
#hydra-save .sbar{flex:1;display:flex;height:.5rem;border-radius:999px;overflow:hidden;background:var(--soft,#eee);border:1px solid var(--line,#d6d4ce)}
#hydra-save .sbar i{display:block;height:100%;background:var(--link,#586c50)}
#hydra-save .items{grid-column:1/-1;padding:.15rem 0 .35rem 1.6rem;border-bottom:1px solid color-mix(in srgb,var(--line,#d6d4ce) 55%,transparent)}
#hydra-save .it{display:grid;grid-template-columns:1.1rem .9rem minmax(0,1fr) auto 1.75rem 1.75rem;column-gap:.45rem;align-items:center;padding:.06rem 0;font-size:.88rem}
#hydra-save .it .ty{color:var(--muted,#666760);font-size:.78rem;white-space:nowrap}
#hydra-save .it .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#hydra-save .mk{font-weight:700;text-align:center;font-variant-numeric:tabular-nums}
#hydra-save .mk.added{color:var(--link,#586c50)}#hydra-save .mk.changed{color:var(--muted,#666760)}#hydra-save .mk.removed{color:var(--red,#b3261e)}
#hydra-save .it.off .t,#hydra-save .row.off .t{color:var(--muted,#666760)}
#hydra-save .more{grid-column:1/-1;justify-self:start;margin:.2rem 0 0 1.55rem;border:0;background:none;color:var(--link,#586c50);font:inherit;font-size:.84rem;cursor:pointer;padding:0}
#hydra-save .diff{grid-column:1/-1;margin:.25rem 0 .45rem 1.55rem;border:1px solid var(--line,#d6d4ce);border-radius:var(--hs-r);overflow:hidden;font-size:.84rem}
#hydra-save .diff table{width:100%;border-collapse:collapse}
#hydra-save .diff th{text-align:left;font-weight:600;font-size:.74rem;color:var(--muted,#666760);background:var(--soft,#eee);padding:.3rem .55rem}
#hydra-save .diff td{vertical-align:top;padding:.3rem .55rem;border-top:1px solid color-mix(in srgb,var(--line,#d6d4ce) 60%,transparent);overflow-wrap:anywhere}
#hydra-save .diff td:first-child{width:9rem;color:var(--muted,#666760)}
#hydra-save .diff del{text-decoration:none;color:var(--red,#b3261e)}#hydra-save .diff ins{text-decoration:none;color:var(--link,#586c50)}
#hydra-save .ver{display:flex;align-items:center;gap:.6rem}
#hydra-save .ver label{font-size:.82rem;font-weight:600;color:var(--muted,#666760)}
#hydra-save .ver input{max-width:14rem}
#hydra-save .sign{display:flex;align-items:center;gap:.4rem;font-size:.88rem;cursor:pointer;white-space:nowrap}
#hydra-save .err{color:var(--red,#b3261e);font-size:.86rem;padding:0 1.15rem .6rem}
#hydra-save .err:empty{display:none}
#hydra-save .log{display:flex;flex-direction:column}
#hydra-save .sv{display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:.6rem;padding:.55rem 0;border-bottom:1px solid color-mix(in srgb,var(--line,#d6d4ce) 55%,transparent)}
#hydra-save .sv .m{font-weight:550;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#hydra-save .sv .d{color:var(--muted,#666760);font-size:.84rem;white-space:pre-line}
#hydra-save .sv .meta{display:flex;flex-wrap:wrap;align-items:center;gap:.45rem;color:var(--muted,#666760);font-size:.8rem;margin-top:.1rem}
#hydra-save .sv .meta svg{width:13px;height:13px;color:var(--link,#586c50)}
#hydra-save .sv .acts{display:flex;gap:.1rem;align-self:start}
#hydra-save .sv .x{grid-column:1/-1;display:flex;flex-wrap:wrap;align-items:center;gap:.4rem .9rem;margin-top:.45rem;font-size:.85rem}
#hydra-save .sv .x .c{font-variant-numeric:tabular-nums}
#hydra-save .sv .x input{max-width:12rem;padding:.3rem .5rem}
#hydra-save .all{align-self:flex-end;margin-top:.5rem;font-size:.86rem;color:var(--link,#586c50)}
`;
    document.documentElement.append(style);

    const holder = document.createElement('span');
    holder.className = 'window-save';
    holder.hidden = true;
    holder.setAttribute('data-webview-ignore', '');
    holder.innerHTML = '<button type="button" data-action="save" title="Save" aria-label="Save"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 1.5h6.5L10.5 3.5V10.5H2z"/><path d="M4 1.5v3h4v-3M4 10.5V7h4v3.5"/></svg></button>';
    nav.after(holder);
    /* Archives (owner BJ3): an icon right of Save, the size of Save, back to the archives' landing page (the shell draws it as text at the right) */
    const shelf = bar.querySelector('.archives-link');
    if (shelf && !shelf.classList.contains('window-archives')) {
        shelf.className = 'archives-link window-archives';
        shelf.title = 'Archives';
        shelf.setAttribute('aria-label', 'Archives');
        shelf.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v14a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z"/><path d="M9 5a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v14a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z"/><path d="M5 8h4"/><path d="M9 16h4"/><path d="M13.803 4.56l2.184 -.53c.562 -.135 1.133 .19 1.282 .732l3.695 13.418a1.02 1.02 0 0 1 -.634 1.219l-.133 .041l-2.184 .53c-.562 .135 -1.133 -.19 -1.282 -.732l-3.695 -13.418a1.02 1.02 0 0 1 .634 -1.219l.133 -.041z"/><path d="M14 9l4 -1"/><path d="M16 16l3.923 -.98"/></svg>';
        holder.after(shelf);
    }
    /* Home (owner BM3): the brand is the button to the startup page */
    const brand = bar.querySelector('.window-brand');
    if (brand) {
        brand.setAttribute('role', 'link');
        brand.tabIndex = 0;
        brand.title = 'Home';
        brand.setAttribute('aria-label', 'Home');
        brand.setAttribute('data-webview-ignore', '');
        const home = () => location.assign('/_desktop/');
        brand.addEventListener('click', home);
        brand.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); home(); } });
    }
    /* Archives menu (owner BM3): the books button drops down open-a-folder and open-a-file. The picker, the load bar and the
       "needs a build" question are the archives page's own, which opens with ?pick=folder|file and runs them there. */
    const shelfBtn = bar.querySelector('.window-archives');
    if (shelfBtn) {
        const menu = document.createElement('div');
        menu.className = 'arch-menu';
        menu.hidden = true;
        menu.setAttribute('role', 'menu');
        menu.setAttribute('data-webview-ignore', '');
        const item = (kind, label, path) => `<button type="button" role="menuitem" data-pick="${kind}" title="${label}" aria-label="${label}"><svg viewBox="0 0 24 24" aria-hidden="true">${path}</svg></button>`;
        menu.innerHTML = item('folder', 'Open archive folder', '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>')
            + item('file', 'Open .hydra file', '<path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 1h5"/>');
        bar.append(menu);
        const shut = () => { menu.hidden = true; shelfBtn.setAttribute('aria-expanded', 'false'); };
        shelfBtn.setAttribute('aria-haspopup', 'menu');
        shelfBtn.setAttribute('aria-expanded', 'false');
        shelfBtn.addEventListener('click', e => {
            e.preventDefault();
            if (!menu.hidden) { shut(); return; }
            const r = shelfBtn.getBoundingClientRect();
            menu.hidden = false;
            menu.style.top = (r.bottom + 2) + 'px';
            menu.style.left = Math.max(4, Math.min(r.left, innerWidth - menu.offsetWidth - 4)) + 'px';
            shelfBtn.setAttribute('aria-expanded', 'true');
            menu.querySelector('button').focus();
        });
        menu.addEventListener('click', e => {
            const b = e.target.closest('button[data-pick]');
            if (b) location.assign('/_desktop/?pick=' + b.dataset.pick);
        });
        document.addEventListener('pointerdown', e => { if (!menu.hidden && !menu.contains(e.target) && !shelfBtn.contains(e.target)) shut(); }, true);
        document.addEventListener('keydown', e => { if (e.key === 'Escape' && !menu.hidden) { shut(); shelfBtn.focus(); } });
        window.addEventListener('blur', shut);
    }
    const button = holder.querySelector('button');

    const getJson = async path => {
        const r = await fetch(path, {cache: 'no-store'});
        const body = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(body.error || String(r.status));
        return body;
    };
    const post = async (path, data) => {
        const r = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Hydra-Save': '1'}, body: JSON.stringify(data)});
        const body = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(body.error || String(r.status));
        return body;
    };
    const poll = async () => {
        if (document.visibilityState !== 'visible') return;
        try {
            const p = await getJson('/_desktop/pending?brief=1');
            holder.hidden = !p.writable;
            holder.toggleAttribute('data-dirty', !!p.dirty);
            button.title = p.dirty ? 'Save (Ctrl+S)' : 'Save';
        } catch (e) { /* the bar works without it */ }
    };
    poll();
    setInterval(poll, 10000);
    document.addEventListener('visibilitychange', poll);
    window.addEventListener('pageshow', poll);
    if (window.navigation) navigation.addEventListener('navigatesuccess', poll);

    /* Lucide icons (ISC, lucide.dev), inline so they take the text's colour */
    const ICON = {
        more: '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
        caret: '<path d="m9 18 6-6-6-6"/>',
        back: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
        diff: '<path d="M12 3v14"/><path d="M5 10h14"/><path d="M5 21h14"/>',
        discard: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
        restore: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
        check: '<path d="M20 6 9 17l-5-5"/>',
        tag: '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>',
        pen: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/>',
        signed: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    };
    const svg = k => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k]}</svg>`;
    const el = (tag, props = {}, ...kids) => {
        const n = document.createElement(tag);
        for (const [k, v] of Object.entries(props)) {
            if (k === 'class') n.className = v;
            else if (k === 'html') n.innerHTML = v;
            else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
            else if (v === true) n.setAttribute(k, '');
            else if (v !== false && v != null) n.setAttribute(k, v);
        }
        n.append(...kids.filter(x => x != null && x !== false));
        return n;
    };
    const ib = (icon, label, onclick, attrs = {}) => el('button', {type: 'button', class: 'ib', title: label, 'aria-label': label, html: svg(icon), onclick, ...attrs});
    /* a button that ends data waits for its check mark: the first press arms it, the second within 4 s acts */
    const armed = (icon, label, act) => {
        let timer = null;
        const b = ib(icon, label, async () => {
            if (!b.hasAttribute('data-armed')) {
                b.setAttribute('data-armed', '');
                b.innerHTML = svg('check');
                timer = setTimeout(() => { b.removeAttribute('data-armed'); b.innerHTML = svg(icon); }, 4000);
                return;
            }
            clearTimeout(timer);
            b.disabled = true;
            try { await act(); } finally { b.disabled = false; b.removeAttribute('data-armed'); b.innerHTML = svg(icon); }
        });
        return b;
    };
    const n0 = n => Number(n || 0).toLocaleString('en');
    const day = t => (t || '').slice(0, 10);
    const MARK = {added: '+', changed: '~', removed: '−', modified: '~'};

    let overlay = null, stale = false, sheet = null, err = null, menu = null, p = null;
    const draft = {message: '', description: '', version: null, open: new Set()};
    const held = {records: new Set(), files: new Set()};
    const rk = (path, id) => path + '\u0000' + id;

    const close = async () => {
        if (!overlay) return;
        overlay.remove();
        overlay = null;
        button.focus();
        if (stale) {                                   // discards or a restore changed the files: build once, then show them
            stale = false;
            holder.setAttribute('data-busy', '');
            try { await post('/_desktop/refresh', {}); } catch (e) { /* the next open shows the error */ }
            holder.removeAttribute('data-busy');
            location.reload();
            return;
        }
        poll();
    };
    const fail = e => { if (err) err.textContent = e.message || String(e); };
    const clearErr = () => { if (err) err.textContent = ''; };

    function frame(title, back, ...extra) {
        const top = el('div', {class: 'hs-top'},
            back ? ib('back', 'Back', back) : null, el('h2', {}, title), ...extra);
        err = el('div', {class: 'err', role: 'alert'});
        sheet.replaceChildren(top);
        return {top, add: (...n) => sheet.append(...n)};
    }

    /* ---------------------------------------------------------------- the Save view */
    async function showSave() {
        try { p = await getJson('/_desktop/pending'); } catch (e) { return fail(e); }
        const more = ib('more', 'More', () => toggleMenu());
        const f = frame('Save', null, more);
        const message = el('input', {type: 'text', maxlength: 200, autocomplete: 'off', placeholder: 'Summary', 'aria-label': 'Summary', value: draft.message});
        const description = el('textarea', {rows: 2, maxlength: 4000, placeholder: 'Details', 'aria-label': 'Details'});
        description.value = draft.description;
        const body = el('div', {class: 'hs-body'}, el('div', {class: 'hs-fields'}, message, description));
        drawChanges(body);
        let version = null;
        if (draft.version !== null) {
            version = el('input', {type: 'text', maxlength: 100, autocomplete: 'off', value: draft.version, 'aria-label': 'Version', id: 'hs-ver'});
            version.addEventListener('input', () => { draft.version = version.value; });
            body.append(el('div', {class: 'ver'}, el('label', {for: 'hs-ver'}, 'Version'), version));
        }
        const ok = el('button', {type: 'submit', class: 'btn pri', disabled: !message.value.trim()}, 'Save');
        let sign = null;
        if (p.signing) {
            let on = false;
            try { on = localStorage.getItem('hydra-save-sign') === '1'; } catch (e) { /* none kept */ }
            sign = el('input', {type: 'checkbox', checked: on});
            sign.addEventListener('change', () => { try { localStorage.setItem('hydra-save-sign', sign.checked ? '1' : '0'); } catch (e) { /* not kept */ } });
        }
        const foot = el('div', {class: 'hs-foot'},
            p.author ? el('span', {class: 'hs-who', title: 'Author'}, p.author) : null,
            sign ? el('label', {class: 'sign'}, sign, 'Sign') : null,
            el('span', {class: 'hs-gap'}),
            el('button', {type: 'button', class: 'btn', onclick: close}, 'Cancel'), ok);
        const form = el('form', {}, body, err, foot);
        form.style.cssText = 'display:flex;flex-direction:column;min-height:0;flex:1';
        f.add(form);
        message.addEventListener('input', () => { draft.message = message.value; ok.disabled = !message.value.trim(); });
        description.addEventListener('input', () => { draft.description = description.value; });
        form.addEventListener('submit', async ev => {
            ev.preventDefault();
            if (!message.value.trim()) return;
            ok.disabled = true;
            clearErr();
            try {
                await post('/_desktop/save', {message: message.value, description: description.value,
                    hold: {records: [...held.records].map(k => k.split('\u0000')), files: [...held.files]},
                    sign: !!(sign && sign.checked), ...(draft.version && draft.version.trim() ? {tag: draft.version.trim()} : {})});
                draft.message = draft.description = '';
                draft.version = null;
                held.records.clear();
                held.files.clear();
                holder.removeAttribute('data-dirty');
                close();
            } catch (e) { fail(e); ok.disabled = false; }
        });
        message.focus();
    }

    /* what goes in: one section per group; only groups with something in them */
    function drawChanges(body) {
        const all = [...p.collections];
        const relOf = new Map();                        // an added entity's id -> the relation items that point at it
        all.forEach(c => c.items.forEach(i => { if (i.edge) (i.ends || []).forEach(e => { if (!relOf.has(e)) relOf.set(e, []); relOf.get(e).push([c, i]); }); }));
        if (all.length) body.append(collections(all, relOf));
        for (const [key, title] of [['review', 'Review'], ['rules', 'Rules'], ['sources', 'Sources'], ['files', 'Files']])
            if ((p[key] || []).length) body.append(plainGroup(title, p[key]));
    }

    const itemHeld = (c, i) => held.records.has(rk(c.path, i.id));
    const colState = c => {
        const n = c.items.filter(i => itemHeld(c, i)).length;
        return n === 0 ? 'on' : n === c.items.length ? 'off' : 'some';
    };
    const setBox = (box, state) => { box.checked = state !== 'off'; box.indeterminate = state === 'some'; };

    function collections(list, relOf) {
        const g = el('div', {class: 'grp'});
        const allBox = el('input', {type: 'checkbox', 'aria-label': 'All collections'});
        const syncAll = () => {
            const s = list.map(colState);
            setBox(allBox, s.every(x => x === 'on') ? 'on' : s.every(x => x === 'off') ? 'off' : 'some');
        };
        const redraws = [];
        allBox.addEventListener('change', () => {
            list.forEach(c => c.items.forEach(i => allBox.checked ? held.records.delete(rk(c.path, i.id)) : held.records.add(rk(c.path, i.id))));
            redraws.forEach(f => f());
            syncAll();
        });
        g.append(el('div', {class: 'gh'}, el('span', {}, allBox), el('h3', {}, 'Collections'), el('span', {class: 'num'}, 'Entities'),
            el('span', {class: 'num'}, 'Relations'), el('span', {class: 'num'}, 'Sources'), el('span', {class: 'bc'}, 'Sourced')));
        for (const c of list) {
            const box = el('input', {type: 'checkbox', 'aria-label': c.title || c.name});
            const pct = c.counted ? c.sourced / c.counted * 100 : 0;
            const tip = c.counted ? `${n0(c.sourced)} of ${n0(c.counted)} sourced` : '';
            const nm = el('div', {class: 'nm', role: 'button', tabindex: 0, 'aria-expanded': 'false'},
                el('span', {html: svg('caret'), class: 'car'}), el('span', {class: 't', title: c.title || c.name}, c.title || c.name),
                c.new ? el('span', {class: 'chip'}, 'New') : null, c.gone ? el('span', {class: 'chip gone'}, 'Removed') : null);
            const row = el('div', {class: 'row'}, el('span', {}, box), nm,
                el('span', {class: 'num'}, c.entities ? n0(c.entities) : ''), el('span', {class: 'num'}, c.relations ? n0(c.relations) : ''),
                el('span', {class: 'num'}, c.sources ? n0(c.sources) : ''),
                el('span', {class: 'bc'}, c.counted ? el('span', {class: 'sbar', title: tip, role: 'img', 'aria-label': tip}, el('i', {style: `width:${pct.toFixed(1)}%`})) : null));
            let items = null;
            const sync = () => {
                const s = colState(c);
                setBox(box, s);
                row.classList.toggle('off', s === 'off');
                if (items) items.querySelectorAll('.it').forEach(r => { const i = r.__item; r.querySelector('input').checked = !itemHeld(c, i); r.classList.toggle('off', itemHeld(c, i)); });
                syncAll();
            };
            redraws.push(sync);
            box.addEventListener('change', () => {
                c.items.forEach(i => box.checked ? held.records.delete(rk(c.path, i.id)) : held.records.add(rk(c.path, i.id)));
                sync();
            });
            const toggle = () => {
                const open = !draft.open.has(c.path);
                open ? draft.open.add(c.path) : draft.open.delete(c.path);
                show(open);
            };
            const show = open => {
                row.classList.toggle('open', open);
                nm.classList.toggle('open', open);
                nm.setAttribute('aria-expanded', String(open));
                if (open && !items) {
                    items = records(c, relOf, () => redraws.forEach(f => f()));
                    row.after(items);
                    sync();
                }
                if (items) items.hidden = !open;
            };
            nm.addEventListener('click', toggle);
            nm.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); toggle(); } });
            g.append(row);
            if (draft.open.has(c.path)) show(true);
            sync();
        }
        return g;
    }

    function records(c, relOf, redraw) {
        const box = el('div', {class: 'items'});
        const STEP = 100;
        let shown = 0;
        const more = el('button', {type: 'button', class: 'more'});
        const add = () => {
            c.items.slice(shown, shown + STEP).forEach(i => box.insertBefore(record(c, i, relOf, redraw), more));
            shown = Math.min(c.items.length, shown + STEP);
            more.textContent = `+ ${n0(c.items.length - shown)} more`;
            more.hidden = shown >= c.items.length;
        };
        more.addEventListener('click', add);
        box.append(more);
        add();
        return box;
    }

    function record(c, i, relOf, redraw) {
        const cb = el('input', {type: 'checkbox', checked: !itemHeld(c, i), 'aria-label': i.name});
        cb.addEventListener('change', () => {
            const k = rk(c.path, i.id);
            if (cb.checked) held.records.delete(k);
            else {
                held.records.add(k);
                if (i.change === 'added') (relOf.get(i.id) || []).forEach(([rc, ri]) => held.records.add(rk(rc.path, ri.id)));   // a link to a record left out stays out with it
            }
            redraw();
        });
        let diff = null;
        const dbtn = ib('diff', 'Diff', async () => {
            if (diff) { diff.remove(); diff = null; dbtn.setAttribute('aria-pressed', 'false'); return; }
            try {
                const d = await getJson(`/_desktop/diff?path=${encodeURIComponent(c.path)}&id=${encodeURIComponent(i.id)}`);
                diff = diffTable(d);
                r.after(diff);
                dbtn.setAttribute('aria-pressed', 'true');
            } catch (e) { fail(e); }
        }, {'aria-pressed': 'false'});
        const r = el('div', {class: 'it'}, cb, el('span', {class: `mk ${i.change}`, title: i.change}, MARK[i.change]),
            el('span', {class: 't', title: i.name}, i.name), el('span', {class: 'ty'}, i.type), dbtn,
            armed('discard', 'Discard', async () => {
                try {
                    await post('/_desktop/discard', {path: c.path, id: i.id});
                    stale = true;
                    held.records.delete(rk(c.path, i.id));
                    keepDraft();
                    await showSave();
                } catch (e) { fail(e); }
            }));
        r.__item = i;
        return r;
    }

    function diffTable(d) {
        const name = v => d.names && d.names[v] ? d.names[v] : v;
        const vals = (list, Tag) => (list || []).map(v => el(Tag, {title: v}, name(v))).reduce((a, x, k) => (k && a.push(', '), a.push(x), a), []);
        const both = d.change === 'changed';
        const head = el('tr', {}, el('th', {}, 'Field'), ...(both ? [el('th', {}, 'Before'), el('th', {}, 'After')] : [el('th', {}, d.change === 'added' ? 'Added' : 'Removed')]));
        const rows = d.fields.map(x => el('tr', {}, el('td', {}, x.label),
            ...(both ? [el('td', {}, ...vals(x.before, 'del')), el('td', {}, ...vals(x.after, 'ins'))]
                     : [el('td', {}, ...vals(d.change === 'added' ? x.after : x.before, d.change === 'added' ? 'ins' : 'del'))])));
        return el('div', {class: 'diff'}, el('table', {}, head, ...rows));
    }

    function plainGroup(title, rows) {
        const g = el('div', {class: 'grp plain'});
        const keys = r => (r.records || []).length ? r.records.map(([pa, id]) => ['r', rk(pa, id)]) : r.files.map(f => ['f', f]);
        const isHeld = r => keys(r).every(([t, k]) => (t === 'r' ? held.records : held.files).has(k));
        const setHeld = (r, on) => keys(r).forEach(([t, k]) => { const s = t === 'r' ? held.records : held.files; on ? s.add(k) : s.delete(k); });
        const allBox = el('input', {type: 'checkbox', 'aria-label': title});
        const boxes = [];
        const sync = () => {
            boxes.forEach(([b, r, row]) => { b.checked = !isHeld(r); row.classList.toggle('off', isHeld(r)); });
            const n = rows.filter(isHeld).length;
            setBox(allBox, n === 0 ? 'on' : n === rows.length ? 'off' : 'some');
        };
        allBox.addEventListener('change', () => { rows.forEach(r => setHeld(r, !allBox.checked)); sync(); });
        g.append(el('div', {class: 'gh'}, el('span', {}, allBox), el('h3', {}, title), el('span'), el('span')));
        for (const r of rows) {
            const b = el('input', {type: 'checkbox', 'aria-label': r.label});
            b.addEventListener('change', () => { setHeld(r, !b.checked); sync(); });
            const discard = armed('discard', 'Discard', async () => {
                try {
                    const rec = (r.records || [])[0];
                    await post('/_desktop/discard', rec ? {path: rec[0], id: rec[1]} : {files: r.files});
                    stale = true;
                    setHeld(r, false);
                    keepDraft();
                    await showSave();
                } catch (e) { fail(e); }
            });
            const nm = el('div', {class: 'nm'}, r.change ? el('span', {class: `mk ${r.change}`, title: r.change}, MARK[r.change]) : null,
                el('span', {class: 't', title: (r.files || []).length ? r.files.join('\n') : r.label}, r.label));
            nm.style.cursor = 'default';
            const row = el('div', {class: 'row'}, el('span', {}, b), nm, el('span', {class: 'num'}, r.n > 1 ? n0(r.n) : ''), el('span', {}, discard));
            boxes.push([b, r, row]);
            g.append(row);
        }
        sync();
        return g;
    }

    function keepDraft() {
        const m = sheet.querySelector('input[aria-label=Summary]'), d = sheet.querySelector('textarea[aria-label=Details]');
        if (m) draft.message = m.value;
        if (d) draft.description = d.value;
    }

    /* ---------------------------------------------------------------- the menu */
    function toggleMenu() {
        if (menu) { menu.remove(); menu = null; return; }
        const item = (icon, label, act) => el('button', {type: 'button', role: 'menuitem', html: svg(icon), onclick: () => { menu.remove(); menu = null; act(); }}, label);
        menu = el('div', {class: 'hs-menu', role: 'menu'},
            draft.version === null ? item('tag', 'Version', () => { keepDraft(); draft.version = ''; showSave().then(() => { const v = sheet.querySelector('#hs-ver'); if (v) v.focus(); }); }) : null,
            p && p.last ? item('pen', 'Amend last save', () => { keepDraft(); showAmend(); }) : null,
            item('restore', 'History', () => { keepDraft(); showLog(); }));
        sheet.append(menu);
        const first = menu.querySelector('button');
        if (first) first.focus();
    }

    /* ---------------------------------------------------------------- amend */
    function showAmend() {
        const last = p.last;
        const f = frame('Amend', () => showSave());
        const message = el('input', {type: 'text', maxlength: 200, autocomplete: 'off', placeholder: 'Summary', 'aria-label': 'Summary', value: last.message});
        const description = el('textarea', {rows: 3, maxlength: 4000, placeholder: 'Details', 'aria-label': 'Details'});
        description.value = last.description || '';
        const ok = el('button', {type: 'submit', class: 'btn pri'}, 'Amend');
        const form = el('form', {}, el('div', {class: 'hs-body'}, el('div', {class: 'hs-fields'}, message, description)), err,
            el('div', {class: 'hs-foot'}, el('span', {class: 'hs-who'}, `${day(last.time)} · ${last.author}`), el('span', {class: 'hs-gap'}),
                el('button', {type: 'button', class: 'btn', onclick: () => showSave()}, 'Cancel'), ok));
        message.addEventListener('input', () => { ok.disabled = !message.value.trim(); });
        form.addEventListener('submit', async ev => {
            ev.preventDefault();
            ok.disabled = true;
            clearErr();
            try { await post('/_desktop/amend', {message: message.value, description: description.value}); await showSave(); }
            catch (e) { fail(e); ok.disabled = false; }
        });
        f.add(form);
        message.focus();
        message.select();
    }

    /* ---------------------------------------------------------------- history */
    async function showLog() {
        let data;
        try { data = await getJson('/_desktop/log'); } catch (e) { return fail(e); }
        const f = frame('History', () => showSave());
        const list = el('div', {class: 'log'});
        for (const s of data.saves) list.append(saveRow(s));
        const body = el('div', {class: 'hs-body'}, list, el('a', {class: 'all', href: '/changes'}, 'All'));
        f.add(body, err);
    }

    function saveRow(s) {
        const x = el('div', {class: 'x', hidden: true});
        const signed = s.verified === 'verified' ? el('span', {html: svg('signed'), title: 'Signed'}) : s.verified === 'bad' ? el('span', {class: 'chip gone'}, 'Signature does not match') : null;
        const tagBtn = ib('tag', 'Version', () => {
            if (!x.hidden && x.dataset.k === 'tag') { x.hidden = true; return; }
            const inp = el('input', {type: 'text', maxlength: 100, 'aria-label': 'Version', placeholder: 'Version'});
            const go = async () => {
                if (!inp.value.trim()) return;
                try { await post('/_desktop/tag', {name: inp.value.trim(), at: s.id}); await showLog(); } catch (e) { fail(e); }
            };
            inp.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); go(); } });
            x.dataset.k = 'tag';
            x.replaceChildren(inp, ib('check', 'Add version', go));
            x.hidden = false;
            inp.focus();
        });
        const restBtn = ib('restore', 'Restore to here', async () => {
            if (!x.hidden && x.dataset.k === 'restore') { x.hidden = true; return; }
            let pv;
            try { pv = await getJson(`/_desktop/restore?at=${encodeURIComponent(s.id)}`); } catch (e) { return fail(e); }
            const bits = pv.collections.map(c => el('span', {class: 'c'}, el('b', {}, c.name), ' ',
                ...[['added', '+'], ['changed', '~'], ['removed', '−']].filter(([k]) => c[k]).map(([k, m]) => el('span', {class: `mk ${k}`}, ` ${m}${n0(c[k])}`))));
            if (pv.files) bits.push(el('span', {class: 'c'}, el('b', {}, 'Files'), ` ~${n0(pv.files)}`));
            x.dataset.k = 'restore';
            x.replaceChildren(...bits, armed('restore', 'Restore', async () => {
                try { await post('/_desktop/restore', {at: s.id, confirm: true}); stale = true; await showLog(); } catch (e) { fail(e); }
            }));
            if (!bits.length) x.prepend(el('span', {class: 'c'}, '='));
            x.hidden = false;
        });
        return el('div', {class: 'sv'},
            el('div', {}, el('div', {class: 'm', title: s.message}, s.message),
                s.description ? el('div', {class: 'd'}, s.description) : null,
                el('div', {class: 'meta'}, el('span', {}, day(s.time)), s.author ? el('span', {}, s.author) : null,
                    ...s.tags.map(t => el('span', {class: 'chip tag'}, t)), signed,
                    el('a', {href: `/changes/${s.id}`, title: s.id}, s.id.slice(0, 8)))),
            el('div', {class: 'acts'}, tagBtn, s.newest ? null : restBtn), x);
    }

    /* ---------------------------------------------------------------- open / close */
    const open = async () => {
        if (overlay) return;
        p = null;
        sheet = el('div', {class: 'hs', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Save'});
        overlay = el('div', {id: 'hydra-save'}, sheet);
        overlay.addEventListener('mousedown', ev => { if (ev.target === overlay) close(); });
        sheet.addEventListener('mousedown', ev => { if (menu && !menu.contains(ev.target) && !ev.target.closest('[aria-label=More]')) { menu.remove(); menu = null; } });
        document.body.append(overlay);
        err = el('div', {class: 'err', role: 'alert'});
        await showSave();
        if (!p) close();
    };
    window.hydraSaveOpen = open;
    button.addEventListener('click', open);
    document.addEventListener('keydown', ev => {
        if (ev.key === 'Escape' && overlay) {
            ev.preventDefault();
            if (menu) { menu.remove(); menu = null; } else close();
        }
        if ((ev.ctrlKey || ev.metaKey) && !ev.shiftKey && !ev.altKey && ev.key.toLowerCase() === 's' && !holder.hidden) {
            ev.preventDefault();
            open();
        }
    });
})();

/* The Profile button: the person's portrait, or their initials on a colour from the code name; opens /_desktop/profile.
   Sits at the bar's right, before the window controls, apart from Save and Archives on the left. */
(() => {
    const bar = document.getElementById('hydra-windowbar');
    const controls = bar && bar.querySelector('.window-controls');
    if (!controls || window.__hydraProfile) return;
    window.__hydraProfile = true;
    const style = document.createElement('style');
    style.textContent = `
#hydra-windowbar .window-profile{display:flex;align-items:center;align-self:stretch;flex:none;app-region:no-drag;-webkit-app-region:no-drag}
#hydra-windowbar .window-profile a{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;overflow:hidden;color:#fff;font:600 10px/1 var(--sans,system-ui,sans-serif);letter-spacing:.02em;text-decoration:none;margin-right:6px;box-shadow:0 0 0 1px var(--line,#d6d4ce)}
#hydra-windowbar .window-profile a:hover{box-shadow:0 0 0 2px var(--accent,#586c50)}
#hydra-windowbar .window-profile img{width:100%;height:100%;object-fit:cover;display:block}
#hydra-windowbar .window-profile[data-rail]{visibility:hidden}   /* the wiki's mini rail, Embedded, stands in its place (wiki/assets/minirail.js) */
`;
    document.documentElement.append(style);
    const holder = document.createElement('span');
    holder.className = 'window-profile';
    holder.setAttribute('data-webview-ignore', '');
    const link = document.createElement('a');
    link.href = '/_desktop/profile';
    link.title = 'Profile';
    link.setAttribute('aria-label', 'Profile');
    holder.append(link);
    controls.before(holder);
    fetch('/_desktop/profile.json', {cache: 'no-store'}).then(r => r.ok ? r.json() : Promise.reject()).then(p => {
        if (p.portrait) {
            const img = document.createElement('img');
            img.alt = '';
            img.src = '/_desktop/profile/' + p.portrait;
            link.append(img);
            return;
        }
        let h = 0;
        for (const c of p.codename) h = (h * 31 + c.charCodeAt(0)) % 360;
        link.style.background = `hsl(${h} 32% 38%)`;
        link.textContent = (p.name || p.codename).split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase();
    }).catch(() => holder.remove());
})();

/* The build behind the reader (a stale archive opened at once, hydra/rebuilder.py): a thin line along the foot of the window
   bar while it runs, and the page read again from the new build when it is done, unless the reader is typing. Quiet
   rebuilds (after a write) show nothing. */
(() => {
    const bar = document.getElementById('hydra-windowbar');
    if (!bar || window.__hydraRebuild) return;
    window.__hydraRebuild = true;
    const style = document.createElement('style');
    style.textContent = `
#hydra-windowbar .window-rebuild{position:absolute;left:0;bottom:0;height:2px;width:0;background:var(--accent,#586c50);transition:width .4s ease;pointer-events:none}
`;
    document.documentElement.append(style);
    let line = null, seen = null;
    const busy = () => { const a = document.activeElement; return a && (a.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)); };
    async function look() {
        let s;
        try { s = await (await fetch('/_desktop/rebuild', {cache: 'no-store'})).json(); } catch (e) { return; }
        if (seen === null) seen = s.n;
        if (s.running && s.shown) {
            if (!line) {
                line = document.createElement('i');
                line.className = 'window-rebuild';
                line.setAttribute('data-webview-ignore', '');
                if (getComputedStyle(bar).position === 'static') bar.style.position = 'relative';
                bar.append(line);
            }
            line.style.width = Math.round(100 * Math.max(0.04, Math.min(1, s.fraction || 0))) + '%';
            return setTimeout(look, 400);
        }
        if (line) {
            line.remove();
            line = null;
            if (s.n !== seen && !busy()) location.reload();          // the new build is in: this page from it
        }
    }
    look();
})();
