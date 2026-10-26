'use strict';
// Data injected by app.py: sessions (index.py; the hidden ones are flagged, see showHidden), theme (themes.py: palette
// catalogue + current choice), home, can_focus (bring an open session's window
// to the front: only under niri), defaults_view (default view, --defaults)
const { sessions: allSessions, show_hidden: initialShowHidden, theme, home, can_focus: canFocus, defaults_view: defaultsView,
        language_setting: initialLanguageSetting, language: initialLanguage,
        system_language: systemLanguage } = window.__DATA__;
let P;   // current palette, read on every graph frame

// ---------- user-facing text ----------
// Every string shown to the user lives here (plus [data-i18n] elements of
// index.html, filled at startup): a translation = one more object in STRINGS
// (+ its code in config.LANGUAGES).
const STRINGS = {
  en: {
    name: 'English',
    locale: 'en-GB',
    searchPlaceholder: 'Search… (title, message, folder)',
    hint: '↑↓ select · Enter resume · Esc ×2 close',
    escAgain: 'Esc again to close',
    legendFolder: 'folder · click: filter',
    legendSession: 'conversation · double-click: resume',
    legendRunning: 'open conversation',
    removeFilter: 'Remove filter',
    justNow: 'just now',
    minutesAgo: n => `${n} min ago`,
    hoursAgo: n => `${n} h ago`,
    yesterday: 'yesterday',
    daysAgo: n => `${n} days ago`,
    conversations: n => `${n} conversation${n > 1 ? 's' : ''}`,
    folderTip: 'click: filter',
    sessionTip: running => `click: select · double-click: ${running ? 'go to it' : 'resume'}`,
    openElsewhereTip: 'click: select · already open elsewhere',
    open: 'open',
    noMatch: 'No conversation matches.',
    showHiddenTitle: n => `Show hidden conversations (${n})`,
    hideHiddenTitle: n => `Hide hidden conversations (${n})`,
    hiddenReasons: { 'no-reply': 'no reply', excluded: 'excluded folder', 'non-interactive': 'non-interactive (claude -p)' },
    resume: 'Resume',
    goToWindow: 'Go to window',
    folderMissing: 'Folder not found',
    folderMissingTag: '⚠ folder not found',
    openElsewhere: 'Already open elsewhere',
    modes: { auto: '◐ auto', dark: '☾ dark', light: '☀ light' },
    modeTitle: 'Light / dark: click to change',
    paletteTitle: 'Colour palette',
    otherPalette: 'Other… (pick a .toml file)',
    backToConfig: name => `↺ Back to config (${name})`,
    languageTitle: 'Language',
    languageAuto: name => `System language (${name})`,
    // Error popup (the inline handler in index.html holds the same text as a fallback)
    errorTitle: 'Session Finder ran into a problem',
    errorLoad: 'The interface could not start.',
    errorLater: 'If nothing looks wrong to you, you can keep using it.',
    errorClose: 'Close',
    errorContinue: 'Continue',
  },
  fr: {
    name: 'Français',
    locale: 'fr-FR',
    searchPlaceholder: 'Rechercher… (titre, message, dossier)',
    hint: '↑↓ choisir · Entrée reprendre · Échap ×2 fermer',
    escAgain: 'Échap encore pour fermer',
    legendFolder: 'dossier · clic : filtrer',
    legendSession: 'conversation · double-clic : reprendre',
    legendRunning: 'conversation ouverte',
    removeFilter: 'Retirer le filtre',
    justNow: 'à l’instant',
    minutesAgo: n => `il y a ${n} min`,
    hoursAgo: n => `il y a ${n} h`,
    yesterday: 'hier',
    daysAgo: n => `il y a ${n} jours`,
    conversations: n => `${n} conversation${n > 1 ? 's' : ''}`,
    folderTip: 'clic : filtrer',
    sessionTip: running => `clic : sélectionner · double-clic : ${running ? 'y aller' : 'reprendre'}`,
    openElsewhereTip: 'clic : sélectionner · déjà ouverte ailleurs',
    open: 'ouverte',
    noMatch: 'Aucune conversation ne correspond.',
    showHiddenTitle: n => `Afficher les conversations masquées (${n})`,
    hideHiddenTitle: n => `Masquer les conversations masquées (${n})`,
    hiddenReasons: { 'no-reply': 'sans réponse', excluded: 'dossier exclu', 'non-interactive': 'non interactive (claude -p)' },
    resume: 'Reprendre',
    goToWindow: 'Aller à la fenêtre',
    folderMissing: 'Dossier introuvable',
    folderMissingTag: '⚠ dossier introuvable',
    openElsewhere: 'Déjà ouverte ailleurs',
    modes: { auto: '◐ auto', dark: '☾ sombre', light: '☀ clair' },
    modeTitle: 'Clair / sombre : cliquer pour changer',
    paletteTitle: 'Palette de couleurs',
    otherPalette: 'Autre… (choisir un fichier .toml)',
    backToConfig: name => `↺ Revenir à la config (${name})`,
    languageTitle: 'Langue',
    languageAuto: name => `Langue du système (${name})`,
    errorTitle: 'Session Finder a rencontré un problème',
    errorLoad: 'L’interface n’a pas pu démarrer.',
    errorLater: 'Si rien ne semble anormal, vous pouvez continuer à l’utiliser.',
    errorClose: 'Fermer',
    errorContinue: 'Continuer',
  },
};
// Language chosen by Python (window choice > config > system locale); a key missing
// from a translation falls back to English. Switching language later: applyLanguage().
let language = initialLanguage;
let languageSetting = initialLanguageSetting;   // "auto" or a language code (what the menu shows as selected)
let T = { ...STRINGS.en, ...STRINGS[language] };
function applyStaticText() {
  document.documentElement.lang = language;
  for (const node of document.querySelectorAll('[data-i18n]')) node.textContent = T[node.dataset.i18n];
  for (const node of document.querySelectorAll('[data-i18n-placeholder]')) node.placeholder = T[node.dataset.i18nPlaceholder];
  for (const node of document.querySelectorAll('[data-i18n-title]')) node.title = T[node.dataset.i18nTitle];
}
applyStaticText();

// ---------- helpers ----------
const DAY = 86400000;
const hexRgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const rgba = (h, a) => `rgba(${hexRgb(h).join(',')},${a})`;
const mix = (a, b, t) => { const A = hexRgb(a), B = hexRgb(b); return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * t))})`; };
// case- and accent-insensitive search ("theme" finds "thème")
const norm = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
// fuzzy fallback (pure, tested through node): `word` matches `hay` if some substring of `hay`
// is within a few edits of it (Sellers' approximate substring matching: typos, partial words)
// FUZZY-BEGIN
const fuzzyBudget = w => w.length < 4 ? 0 : w.length < 7 ? 1 : 2;
function fuzzyIncludes(hay, word) {
  if (hay.includes(word)) return true;
  const k = fuzzyBudget(word);
  if (!k) return false;
  let prev = Array.from({ length: word.length + 1 }, (_, i) => i);   // free start anywhere in hay
  for (let j = 0; j < hay.length; j++) {
    const row = [0];
    for (let i = 1; i <= word.length; i++)
      row[i] = Math.min(prev[i] + 1, row[i - 1] + 1, prev[i - 1] + (word[i - 1] === hay[j] ? 0 : 1));
    if (row[word.length] <= k) return true;
    prev = row;
  }
  return false;
}
// FUZZY-END
const short = p => p === home ? '~' : p.startsWith(home + '/') ? '~' + p.slice(home.length) : p;
const ageDays = s => (Date.now() - Date.parse(s.updated || s.created)) / DAY;
function ago(s) {
  const d = ageDays(s);
  if (d < 1 / 1440) return T.justNow;
  if (d < 1 / 24) return T.minutesAgo(Math.round(d * 1440));
  if (d < 1) return T.hoursAgo(Math.round(d * 24));
  if (d < 2) return T.yesterday;
  if (d < 30) return T.daysAgo(Math.round(d));
  return new Date(s.updated).toLocaleDateString(T.locale);
}
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

// ---------- theme: chosen palette + light / dark / auto ----------
// Palette -> CSS variables (style.css has no hard-coded colour)
const rootStyle = document.documentElement.style;
const systemDark = window.matchMedia('(prefers-color-scheme: dark)');
const catalog = theme.catalog;
let current = catalog.find(c => c.id === theme.selected) || catalog[0];
let mode = theme.mode;   // auto | dark | light (no effect on a fixed palette)
function applyPalette() {
  const variant = mode === 'auto' ? (systemDark.matches ? 'dark' : 'light') : mode;
  P = current.palettes[variant];
  for (const [k, v] of Object.entries(P)) {
    const name = '--' + k.toLowerCase().replace(/_/g, '-');
    rootStyle.setProperty(name, v);
    rootStyle.setProperty(name + '-rgb', hexRgb(v).join(','));
  }
}
applyPalette();
systemDark.addEventListener('change', () => { if (mode === 'auto') applyPalette(); });
// translucent background only on request (useful when the compositor blurs behind)
rootStyle.setProperty('--main-alpha', theme.translucent ? 0.82 : 1);

// ---------- graph: tree of launch folders ----------
// "Compressed" tree: only the root, launch folders and branching points are
// kept; a chain of folders without sessions becomes a single node
// (e.g. "Courses/Linux_Admin/exercises").
const parentOf = p => p.slice(0, p.lastIndexOf('/')) || '/';
const under = (p, r) => p === r || p.startsWith(r === '/' ? '/' : r + '/');
for (const s of allSessions) s.cwd = s.cwd || home;
let showHidden = !!initialShowHidden;   // the eye button; remembered in the state
let sessions, rootPath, dirParent, nodes, links, nodeById;   // set by buildTree()

function buildTree() {
  sessions = allSessions.filter(s => showHidden || !s.hidden);
  const cwds = [...new Set(sessions.map(s => s.cwd))];
  rootPath = cwds.every(c => under(c, home)) ? home : '/';

  const children = new Map();
  for (const c of cwds) {
    for (let p = c; p !== rootPath; p = parentOf(p)) {
      const q = parentOf(p);
      if (!children.has(q)) children.set(q, new Set());
      children.get(q).add(p);
    }
  }
  const cwdSet = new Set(cwds);
  const keep = p => p === rootPath || cwdSet.has(p) || (children.get(p)?.size || 0) >= 2;
  const dirPaths = new Set([rootPath]);
  for (const c of cwds) for (let p = c; ; p = parentOf(p)) { if (keep(p)) dirPaths.add(p); if (p === rootPath) break; }

  dirParent = new Map();   // kept folder -> kept parent folder
  for (const d of dirPaths) {
    if (d === rootPath) continue;
    let a = parentOf(d);
    while (!dirPaths.has(a)) a = parentOf(a);
    dirParent.set(d, a);
  }

  nodes = []; links = []; nodeById = new Map();
  for (const d of dirPaths) {
    const parent = dirParent.get(d);
    const label = parent == null ? short(d) : d.slice(parent === '/' ? 1 : parent.length + 1);
    nodes.push({ id: 'd:' + d, kind: 'dir', path: d, label, count: 0 });
    if (parent != null) links.push({ source: 'd:' + parent, target: 'd:' + d, kind: 'dir' });
  }
  for (const s of sessions) {
    nodes.push({ id: 's:' + s.id, kind: 'session', s });
    links.push({ source: 'd:' + s.cwd, target: 's:' + s.id, kind: 'session' });
  }
  for (const n of nodes) nodeById.set(n.id, n);
  // folder weight = sessions it contains, subfolders included
  for (const s of sessions) for (let d = s.cwd; d != null; d = dirParent.get(d)) nodeById.get('d:' + d).count++;
}
buildTree();

const radius = n => n.kind === 'dir' ? 5 + Math.sqrt(n.count) * 1.8 : 2 + Math.sqrt(n.s.user_messages) * 0.8;
// recent = accent colour, fading to FG_DIM over 30 days
const recency = s => mix(P.ACCENT, P.FG_DIM, Math.min(ageDays(s) / 30, 1));

// ---------- state ----------
// Two separate hover sources: the mouse over the graph (magnet) and the mouse
// over the list. The list one is reset on every rebuild: an element removed
// under the cursor never fires "mouseleave" (ghost hover).
let graphHover = null, listHover = null;
const hovered = () => graphHover || listHover;
let scope = null;        // folder filtered by click (null = all)
let matches = null;      // Set of session ids kept by search + folder (null = no filter)
let selectedId = null;
let visible = [];        // sessions shown in the list, in order

function ancestorsOf(s) {
  const ids = [];
  for (let d = s.cwd; d != null; d = dirParent.get(d)) ids.push('d:' + d);
  return ids;
}

// Lit nodes: hover first (temporary), otherwise the filter result
function litSet() {
  const h = hovered();
  if (h) {
    const lit = new Set([h.id]);
    if (h.kind === 'session') ancestorsOf(h.s).forEach(i => lit.add(i));
    else for (const s of sessions) if (under(s.cwd, h.path)) { lit.add('s:' + s.id); ancestorsOf(s).forEach(i => lit.add(i)); }
    return lit;
  }
  if (!matches) return null;
  const lit = new Set();
  for (const s of sessions) if (matches.has(s.id)) { lit.add('s:' + s.id); ancestorsOf(s).forEach(i => lit.add(i)); }
  return lit;
}
let lit = null;
const refreshLit = () => { lit = litSet(); };
const isLit = id => !lit || lit.has(id);

// ---------- graph rendering ----------
const graphEl = document.getElementById('graph');
const tipEl = document.getElementById('tip');

const fg = ForceGraph()(graphEl)
  .graphData({ nodes, links })
  .backgroundColor('rgba(0,0,0,0)')
  .nodeRelSize(1)
  .nodeVal(n => radius(n) ** 2)
  .nodeLabel(() => '')   // no native tooltip: ours follows the magnet (#tip)
  .linkColor(l => {
    const on = isLit(l.source.id) && isLit(l.target.id);
    return rgba(P.FG, l.kind === 'dir' ? (on ? 0.35 : 0.06) : (on ? 0.18 : 0.04));
  })
  .linkWidth(l => l.kind === 'dir' ? 1.2 : 0.6)
  .nodeCanvasObject(drawNode)
  .nodePointerAreaPaint((n, color, ctx, scale) => {
    // grab area (drag and drop) of at least 8 screen px, even zoomed out
    ctx.fillStyle = color; ctx.beginPath();
    ctx.arc(n.x, n.y, Math.max(radius(n) + 2, 8 / scale), 0, 2 * Math.PI); ctx.fill();
  })
  .onNodeClick(n => clickNode(n))
  .onBackgroundClick(() => { if (graphHover) clickNode(graphHover); })  // "magnetic" click next to a node
  .onNodeDrag(() => { tipEl.hidden = true; })
  // Continuous redraw: needed for the animated aura, and keeps the display from
  // freezing when state changes without mouse movement (force-graph's idle pause)
  .autoPauseRedraw(false)
  .d3VelocityDecay(0.3)
  .cooldownTime(6000);

fg.d3Force('charge').strength(n => n.kind === 'dir' ? -260 : -40);
fg.d3Force('link').distance(l => l.kind === 'dir' ? 80 : 26).strength(l => l.kind === 'dir' ? 0.5 : 0.9);

let fitted = false;
fg.onEngineStop(() => { if (!fitted) { fitted = true; fg.zoomToFit(500, 50); } });

// --- Aim assist ("magnet"): the node closest to the cursor within a fixed
// radius in SCREEN pixels, whatever the zoom. Distance measured to the node's
// edge, not its centre: a big folder does not shadow its small neighbours.
const MAGNET_PX = 22;
function nearestNode(clientX, clientY) {
  const box = graphEl.getBoundingClientRect();
  const p = fg.screen2GraphCoords(clientX - box.left, clientY - box.top);
  const scale = fg.zoom();
  let best = null, bestDist = MAGNET_PX / scale;
  for (const n of nodes) {
    if (n.x == null) continue;
    const d = Math.max(0, Math.hypot(n.x - p.x, n.y - p.y) - radius(n));
    if (d < bestDist) { best = n; bestDist = d; }
  }
  return best;
}

graphEl.addEventListener('mousemove', e => {
  if (e.buttons) return;   // while dragging, keep the same target
  const n = nearestNode(e.clientX, e.clientY);
  if (n !== graphHover) { graphHover = n; refreshLit(); }
  graphEl.style.cursor = n ? 'pointer' : null;
  showTip(n, e.clientX, e.clientY);
});
graphEl.addEventListener('mouseleave', () => { graphHover = null; refreshLit(); tipEl.hidden = true; });

function showTip(n, x, y) {
  if (!n) { tipEl.hidden = true; return; }
  tipEl.textContent = '';
  if (n.kind === 'dir') {
    tipEl.append((() => { const t = el('div', 'tip-title', ' ' + short(n.path)); t.prepend(el('span', 'folder-ico')); return t; })(),
                 el('div', 'tip-hint', `${T.conversations(n.count)} · ${T.folderTip}`));
  } else {
    tipEl.append(el('div', 'tip-title', n.s.title),
                 el('div', 'tip-hint', `${ago(n.s)} · ` +
                   (n.s.running && !canFocus ? T.openElsewhereTip : T.sessionTip(Boolean(n.s.running)))));
  }
  tipEl.hidden = false;
  const box = graphEl.getBoundingClientRect();
  // right of the cursor, or left when it would overflow the graph
  const left = x - box.left + 16 + tipEl.offsetWidth > box.width ? x - box.left - 16 - tipEl.offsetWidth : x - box.left + 16;
  tipEl.style.left = `${left}px`;
  tipEl.style.top = `${y - box.top + 14}px`;
}

let lastClick = { id: null, t: 0 };
function clickNode(n) {
  if (n.kind === 'dir') { setScope(scope === n.path ? null : n.path); return; }
  const now = Date.now();
  if (lastClick.id === n.id && now - lastClick.t < 400) resume(n.s);   // double click
  lastClick = { id: n.id, t: now };
  select(n.s.id, { center: false });
}

// Folder icon drawn as a vector (16x16 box): no dependency on an installed icon font.
const FOLDER_PATH = new Path2D('M1 3.5h5l1.5 1.7H15v7.8H1z');
function drawNode(n, ctx, scale) {
  const h = n === hovered();
  const r = radius(n) * (h ? 1.15 : 1);
  const on = isLit(n.id);
  const sel = n.kind === 'session' && n.s.id === selectedId;
  ctx.globalAlpha = on ? 1 : 0.12;

  // Aura of an open session: two waves moving out and fading, like a point of
  // interest on a game minimap. Sizes in screen pixels (/scale).
  if (n.kind === 'session' && n.s.running) {
    const t = (performance.now() % 2200) / 2200;
    for (const phase of [t, (t + 0.5) % 1]) {
      ctx.beginPath(); ctx.arc(n.x, n.y, r + (2 + phase * 22) / scale, 0, 2 * Math.PI);
      ctx.lineWidth = 2 / scale; ctx.strokeStyle = rgba(P.SUCCESS, (1 - phase) * 0.7 * (on ? 1 : 0.3)); ctx.stroke();
    }
    ctx.beginPath(); ctx.arc(n.x, n.y, r + 1.5 / scale, 0, 2 * Math.PI);
    ctx.lineWidth = 1.5 / scale; ctx.strokeStyle = P.SUCCESS; ctx.stroke();
  }

  // Hover glow (shadowBlur is in screen pixels, independent of zoom)
  if (h) { ctx.shadowColor = n.kind === 'dir' ? P.FG : P.ACCENT; ctx.shadowBlur = 18; }
  ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
  if (n.kind === 'dir') {
    ctx.fillStyle = n.path === scope ? P.ACCENT : (n.path === rootPath ? P.ACCENT_ALT : P.BG_ELEVATED);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.lineWidth = 1.2 / scale; ctx.strokeStyle = rgba(P.FG, h ? 0.9 : 0.5); ctx.stroke();
    // folder icon inside the node: clearly not a conversation (16-unit path
    // centred on the node, ~1.1 r wide)
    const k = r * 1.1 / 16;
    ctx.save();
    ctx.translate(n.x - 8 * k, n.y - 8 * k); ctx.scale(k, k);
    ctx.fillStyle = rgba(P.FG, 0.85); ctx.fill(FOLDER_PATH);
    ctx.restore();
  } else {
    ctx.fillStyle = recency(n.s);
    ctx.fill();
    ctx.shadowBlur = 0;
  }
  if (sel) {
    ctx.beginPath(); ctx.arc(n.x, n.y, r + 4 / scale + 2, 0, 2 * Math.PI);
    ctx.lineWidth = 2 / scale; ctx.strokeStyle = P.ACCENT; ctx.stroke();
  }

  // Labels: always for folders; for sessions only when selected / hovered /
  // few filter results / zoomed in enough
  const showLabel = n.kind === 'dir' || sel || h ||
    (matches && matches.size <= 12 && on) || (scale > 3.5 && on);
  if (showLabel) {
    const text = n.kind === 'dir' ? n.label : n.s.title;
    const size = (n.kind === 'dir' ? 12 : 11) / scale;
    ctx.font = `${n.kind === 'dir' ? 'bold ' : ''}${size}px "JetBrainsMono Nerd Font", monospace`;
    // folders below the node, sessions above: a session stuck to its folder
    // no longer hides the folder's name
    const below = n.kind === 'dir';
    ctx.textAlign = 'center'; ctx.textBaseline = below ? 'top' : 'bottom';
    const y = below ? n.y + r + 3 / scale : n.y - r - 3 / scale;
    const t = text.length > 48 ? text.slice(0, 47) + '…' : text;
    ctx.lineWidth = 3 / scale; ctx.strokeStyle = rgba(P.BG, 0.9); ctx.strokeText(t, n.x, y);
    ctx.fillStyle = sel ? P.ACCENT : P.FG;
    ctx.fillText(t, n.x, y);
  }
  ctx.globalAlpha = 1;
}

function fitSize() { fg.width(graphEl.clientWidth).height(graphEl.clientHeight); }
window.addEventListener('resize', fitSize);
fitSize();

// ---------- list (grouped by location) ----------
const listEl = document.getElementById('list');
const searchEl = document.getElementById('search');
const statusEl = document.getElementById('status');
const scopeEl = document.getElementById('scope');
const countEl = document.getElementById('count');
countEl.textContent = sessions.length;

const byPlace = (a, b) => short(a).localeCompare(short(b), T.locale);

function render() {
  listHover = null;   // elements are about to be replaced: see the comment on state
  listEl.textContent = '';
  const groups = new Map();
  for (const s of sessions) {
    if (matches && !matches.has(s.id)) continue;
    if (!groups.has(s.cwd)) groups.set(s.cwd, []);
    groups.get(s.cwd).push(s);
  }
  visible = [];
  for (const cwd of [...groups.keys()].sort(byPlace)) {
    const items = groups.get(cwd).sort((a, b) => (b.updated || '').localeCompare(a.updated || ''));
    const head = el('div', 'group', short(cwd));
    if (!items[0].cwd_exists) head.append(el('span', 'missing-flag', T.folderMissingTag));
    listEl.append(head);
    for (const s of items) { visible.push(s); listEl.append(itemEl(s)); }
  }
  if (!visible.length) listEl.append(el('div', 'empty', T.noMatch));
  if (!visible.some(s => s.id === selectedId)) selectedId = visible[0]?.id ?? null;
  markSelected();
  refreshLit();
}

function itemEl(s) {
  const item = el('div', 'item');
  item.dataset.id = s.id;
  item.setAttribute('role', 'option');
  const name = el('div', 'name');
  if (s.title_source === 'custom') name.append(el('span', 'mark-custom', '✎ '));
  if (s.running) name.append(el('span', 'mark-running', '● '));
  name.append(s.title);
  const meta = [ago(s), `${s.user_messages} msg`];
  if (s.git_branch && s.git_branch !== 'HEAD') meta.push(s.git_branch);
  if (s.running) meta.push(T.open);
  if (s.hidden || s.non_interactive) meta.push(T.hiddenReasons[s.hidden_reason || 'non-interactive']);
  item.append(name, el('div', 'meta', meta.join(' · ')));

  const details = el('div', 'details');
  const prompt = s.last_prompt || s.first_prompt;
  if (prompt) details.append(el('div', 'prompt', prompt));
  details.append(el('div', 'path', `${short(s.cwd)} · ${s.id.slice(0, 8)}`));
  const btn = el('button', s.running ? 'running' : '', s.running ? T.goToWindow : T.resume);
  if (!s.cwd_exists && !s.running) { btn.disabled = true; btn.textContent = T.folderMissing; }
  if (s.running && !canFocus) { btn.disabled = true; btn.textContent = T.openElsewhere; }
  btn.addEventListener('click', e => { e.stopPropagation(); resume(s); });
  details.append(btn);
  item.append(details);

  item.addEventListener('click', () => select(s.id, { center: true }));
  item.addEventListener('dblclick', () => resume(s));
  item.addEventListener('mouseenter', () => { listHover = nodeById.get('s:' + s.id); refreshLit(); });
  item.addEventListener('mouseleave', () => { listHover = null; refreshLit(); });
  return item;
}
listEl.addEventListener('mouseleave', () => { listHover = null; refreshLit(); });

function markSelected() {
  for (const it of listEl.querySelectorAll('.item')) it.classList.toggle('selected', it.dataset.id === selectedId);
}

function select(id, { center = true, scroll = true } = {}) {
  selectedId = id;
  markSelected();
  const item = listEl.querySelector(`.item[data-id="${id}"]`);
  if (item && scroll) item.scrollIntoView({ block: 'nearest' });
  const n = nodeById.get('s:' + id);
  if (center && n && n.x != null) { fg.centerAt(n.x, n.y, 500); if (fg.zoom() < 2.5) fg.zoom(2.5, 500); }
}

function move(step) {
  if (!visible.length) return;
  const i = visible.findIndex(s => s.id === selectedId);
  const next = Math.min(Math.max(i + step, 0), visible.length - 1);
  select(visible[next].id);
}

// ---------- filters: search + folder ----------
function applyFilters() {
  const words = norm(searchEl.value).split(/\s+/).filter(Boolean);
  if (!words.length && !scope) matches = null;
  else {
    matches = new Set();
    const hays = [];
    for (const s of sessions) {
      if (scope && !under(s.cwd, scope)) continue;
      const hay = norm([s.title, s.first_prompt, s.last_prompt, short(s.cwd), s.id.slice(0, 8), s.git_branch].join(' '));
      hays.push([s.id, hay]);
      if (words.every(w => hay.includes(w))) matches.add(s.id);
    }
    // nothing matches exactly: tolerate typos (exact results always come first, alone)
    if (!matches.size && words.length)
      for (const [id, hay] of hays) if (words.every(w => fuzzyIncludes(hay, w))) matches.add(id);
  }
  render();
  if (matches && matches.size) fg.zoomToFit(500, 80, n => lit.has(n.id));   // frame the results
  else if (!matches) fg.zoomToFit(500, 50);
}
searchEl.addEventListener('input', applyFilters);

function setScope(path) {
  scope = path;
  scopeEl.hidden = !path;
  if (path) {
    const sp = scopeEl.querySelector('.scope-path');
    sp.textContent = ' ' + short(path);
    sp.prepend(el('span', 'folder-ico'));
  }
  applyFilters();
}
scopeEl.querySelector('button').addEventListener('click', () => setScope(null));

// ---------- eye button: show / hide the hidden conversations ----------
const eyeBtn = document.getElementById('show-hidden');
const hiddenCount = allSessions.filter(s => s.hidden).length;
function showEyeBtn() {
  eyeBtn.setAttribute('aria-pressed', showHidden);
  eyeBtn.title = (showHidden ? T.hideHiddenTitle : T.showHiddenTitle)(hiddenCount);
}
eyeBtn.addEventListener('click', () => {
  showHidden = !showHidden;
  buildTree();
  fg.graphData({ nodes, links });
  countEl.textContent = sessions.length;
  showEyeBtn();
  applyFilters();
  window.pywebview?.api.set_show_hidden(showHidden);
});
showEyeBtn();

// ---------- light / dark toggle (hidden for a single-variant palette) ----------
const modeBtn = document.getElementById('mode');
const NEXT_MODE = { auto: 'dark', dark: 'light', light: 'auto' };
function showMode() {
  modeBtn.hidden = current.fixed;
  modeBtn.textContent = T.modes[mode];
  modeBtn.title = T.modeTitle;
}
showMode();
modeBtn.addEventListener('click', () => {
  mode = NEXT_MODE[mode];
  applyPalette();
  showMode();
  window.pywebview?.api.set_mode(mode);   // remembered for next time
  searchEl.focus();
});

// ---------- Palette menu: presets, personal palettes, "Other…" ----------
// Instant preview on click; choice remembered on the Python side (state), never
// written to config.toml. Picking the config's palette = clearing the remembered choice.
const paletteBtn = document.getElementById('palette');
const menuEl = document.getElementById('palette-menu');
const languageMenuEl = document.getElementById('language-menu');
const anyMenuOpen = () => !menuEl.hidden || !languageMenuEl.hidden;
function showPaletteBtn() { paletteBtn.textContent = `${current.name} ▾`; paletteBtn.title = T.paletteTitle; }

function usePalette(choice) {
  if (!catalog.some(c => c.id === choice.id)) catalog.push(choice);
  current = choice;
  applyPalette();
  showMode();
  showPaletteBtn();
  window.pywebview?.api.set_palette(choice.id === theme.config_selected ? null : choice.id);
}

function swatches(choice) {
  const box = el('span', 'swatches');
  const p = choice.palettes.dark;
  for (const k of ['BG', 'ACCENT', 'ACCENT_ALT', 'FG']) {
    const dot = el('span', 'swatch');
    dot.style.background = p[k];
    box.append(dot);
  }
  return box;
}

function menuItem(label, onClick, { choice = null, cls = '' } = {}) {
  const item = el('button', `menu-item ${cls}`);
  item.type = 'button';
  if (choice) {
    item.append(el('span', 'menu-mark', choice.id === current.id ? '●' : '○'), el('span', 'menu-label', label), swatches(choice));
  } else item.append(el('span', 'menu-label', label));
  item.addEventListener('click', e => { e.stopPropagation(); closeMenu(); onClick(); });
  return item;
}

function openMenu() {
  menuEl.textContent = '';
  for (const c of catalog) menuEl.append(menuItem(c.name, () => usePalette(c), { choice: c }));
  menuEl.append(el('div', 'menu-sep'));
  menuEl.append(menuItem(T.otherPalette, browsePalette));
  if (!defaultsView && current.id !== theme.config_selected) {
    const fromConfig = catalog.find(c => c.id === theme.config_selected);
    if (fromConfig) menuEl.append(menuItem(T.backToConfig(fromConfig.name), () => usePalette(fromConfig)));
  }
  menuEl.hidden = false;
}
function closeMenu() { menuEl.hidden = true; languageMenuEl.hidden = true; searchEl.focus(); }

async function browsePalette() {
  if (!window.pywebview?.api) return;
  statusEl.textContent = '';
  const res = await window.pywebview.api.browse_palette();
  if (!res) return;                       // dialog cancelled
  if (res.error) { statusEl.textContent = res.error; return; }
  usePalette(catalog.find(c => c.id === res.id) || res);
}

showPaletteBtn();
paletteBtn.addEventListener('click', e => {
  e.stopPropagation();
  const wasOpen = !menuEl.hidden;
  closeMenu();
  if (!wasOpen) openMenu();
});
document.addEventListener('click', e => {
  if (anyMenuOpen() && !menuEl.contains(e.target) && !languageMenuEl.contains(e.target)) closeMenu();
});

// ---------- Language menu: "System language" + one entry per STRINGS language ----------
// Applied instantly; choice remembered on the Python side (state), never in config.toml.
const languageBtn = document.getElementById('language');
const resolvedLanguage = setting => setting === 'auto' ? systemLanguage : setting;
function showLanguageBtn() {
  languageBtn.textContent = `${language.toUpperCase()} ▾`;
  languageBtn.title = T.languageTitle;
}
function applyLanguage(setting) {
  languageSetting = setting;
  language = resolvedLanguage(setting);
  T = { ...STRINGS.en, ...STRINGS[language] };
  applyStaticText();
  showMode();
  showPaletteBtn();
  showLanguageBtn();
  showEyeBtn();
  hintEl.textContent = T.hint;
  hintEl.classList.remove('armed');
  render();
  window.pywebview?.api.set_language(setting);
}
function openLanguageMenu() {
  languageMenuEl.textContent = '';
  const entry = (setting, label) => {
    const item = el('button', 'menu-item');
    item.type = 'button';
    item.append(el('span', 'menu-mark', setting === languageSetting ? '●' : '○'), el('span', 'menu-label', label));
    item.addEventListener('click', e => { e.stopPropagation(); closeMenu(); if (setting !== languageSetting) applyLanguage(setting); });
    languageMenuEl.append(item);
  };
  entry('auto', T.languageAuto((STRINGS[systemLanguage] || STRINGS.en).name));
  languageMenuEl.append(el('div', 'menu-sep'));
  for (const code of Object.keys(STRINGS)) entry(code, STRINGS[code].name);
  languageMenuEl.hidden = false;
}
languageBtn.addEventListener('click', e => {
  e.stopPropagation();
  const wasOpen = !languageMenuEl.hidden;
  closeMenu();
  if (!wasOpen) openLanguageMenu();
});
showLanguageBtn();

// ---------- actions ----------
async function resume(s) {
  if (!window.pywebview?.api) return;
  statusEl.textContent = '';
  const res = await window.pywebview.api.resume(s.id);
  if (res && !res.ok) statusEl.textContent = res.error;
}

// Esc: clears the search, then the folder filter, then closes with TWO presses.
// The 2nd one must come between 80 ms (below: key bounce/drift) and 1.5 s;
// auto-repeat of a held key is ignored.
const CLOSE_MIN_MS = 80, CLOSE_MAX_MS = 1500;
let closeArmedAt = 0, closeTimer = null;
const hintEl = document.getElementById('hint');
function escape(e) {
  if (e.repeat) return;
  if (anyMenuOpen()) { closeMenu(); return; }
  if (searchEl.value) { searchEl.value = ''; applyFilters(); return; }
  if (scope) { setScope(null); return; }
  const dt = performance.now() - closeArmedAt;
  if (closeArmedAt && dt >= CLOSE_MIN_MS && dt <= CLOSE_MAX_MS) { window.pywebview?.api.close(); return; }
  if (closeArmedAt && dt < CLOSE_MIN_MS) return;
  closeArmedAt = performance.now();
  hintEl.textContent = T.escAgain;
  hintEl.classList.add('armed');
  clearTimeout(closeTimer);
  closeTimer = setTimeout(() => { closeArmedAt = 0; hintEl.textContent = T.hint; hintEl.classList.remove('armed'); }, CLOSE_MAX_MS);
}

document.addEventListener('keydown', e => {
  if (anyMenuOpen() && e.key !== 'Escape') return;   // a menu is open: no action on the list
  if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
  else if (e.key === 'Enter') { const s = sessions.find(x => x.id === selectedId); if (s) resume(s); }
  else if (e.key === 'Escape') escape(e);
  else if (document.activeElement !== searchEl && e.key.length === 1 && !e.ctrlKey && !e.altKey) {
    searchEl.focus();   // typing anywhere = typing in the search box
  }
});

render();
searchEl.focus();

window.__appReady = true;   // read by the error handler in index.html
