"use strict";

/* ================= Utilitare ================= */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const MONTHS = ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie", "Iulie",
  "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"];

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

const numberFmt = new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 0 });
const numberFmt2 = new Intl.NumberFormat("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const lei = (v, decimals = false) => `${(decimals ? numberFmt2 : numberFmt).format(v || 0)} lei`;
const pct = (v) => `${new Intl.NumberFormat("ro-RO", { maximumFractionDigits: 1 }).format(v || 0)}%`;

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
const currentMonth = () => todayISO().slice(0, 7);
function shiftMonth(ym, delta) {
  const [y, m] = ym.split("-").map(Number);
  const idx = y * 12 + (m - 1) + delta;
  return `${Math.floor(idx / 12)}-${String((idx % 12) + 1).padStart(2, "0")}`;
}
function monthLabel(ym) {
  const [y, m] = ym.split("-").map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}
function formatDate(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}
const initials = (name) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
const GRADIENTS = [
  ["#22d3ee", "#3b82f6"], ["#fde68a", "#f59e0b"], ["#a78bfa", "#6366f1"],
  ["#34d399", "#059669"], ["#f9a8d4", "#ec4899"], ["#fdba74", "#f97316"],
];
function gradientFor(name) {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const [a, b] = GRADIENTS[h % GRADIENTS.length];
  return `linear-gradient(135deg, ${a}, ${b})`;
}

/* ================= Iconițe ================= */

const ICONS = {
  dashboard: '<path d="M3 13h8V3H3zM13 21h8V11h-8zM3 21h8v-6H3zM13 3v6h8V3z"/>',
  sales: '<path d="M3 3h2l2.4 12.2a2 2 0 002 1.8h8.9a2 2 0 002-1.6L22 7H6"/><circle cx="9" cy="21" r="1"/><circle cx="18" cy="21" r="1"/>',
  expenses: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
  team: '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.9M16 3.1a4 4 0 010 7.8"/>',
  taxes: '<path d="M4 2v20l3-2 3 2 3-2 3 2 3-2 1 .7V2l-1 .7-3-2-3 2-3-2-3 2-3-2z"/><path d="M9 8l6 6M9.5 14h0M14.5 8h0"/>',
  reports: '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  edit: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4z"/>',
  trash: '<path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>',
  up: '<path d="M12 19V5M5 12l7-7 7 7"/>',
  down: '<path d="M12 5v14M19 12l-7 7-7-7"/>',
  trend: '<path d="M23 6l-9.5 9.5-5-5L1 18"/><path d="M17 6h6v6"/>',
  wallet: '<path d="M21 12V7H5a2 2 0 010-4h14v4"/><path d="M3 5v14a2 2 0 002 2h16v-5"/><path d="M18 12a2 2 0 000 4h4v-4z"/>',
  alert: '<path d="M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/><path d="M12 9v4M12 17h0"/>',
  percent: '<path d="M19 5L5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
  star: '<path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
  coins: '<circle cx="8" cy="8" r="6"/><path d="M18.1 10.4A6 6 0 1110.4 18.1M7 6h1v4M16.7 13.9l.7.7-2.8 2.8"/>',
  profit: '<path d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
  user: '<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  excel: '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M8 12l5 6M13 12l-5 6"/>',
  pdf: '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M9 15h6M9 18h4M9 12h2"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3"/>',
  check: '<path d="M20 6L9 17l-5-5"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>',
  money: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 12h0M18 12h0"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  box: '<path d="M21 16V8a2 2 0 00-1-1.7l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.7l7 4a2 2 0 002 0l7-4a2 2 0 001-1.7z"/><path d="M3.3 7L12 12l8.7-5M12 22V12"/>',
  raise: '<path d="M12 20V10M18 20V4M6 20v-4"/>',
  truck: '<path d="M1 3h15v13H1zM16 8h4l3 3v5h-7z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
  users: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 016-6h4a6 6 0 016 6v1"/><path d="M19 4.5a3 3 0 010 5.5M5 4.5a3 3 0 000 5.5"/>',
  undo: '<path d="M3 7v6h6"/><path d="M21 17a9 9 0 00-15-6.7L3 13"/>',
  bank: '<path d="M3 10l9-6 9 6M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 21h18"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/>',
  history: '<path d="M3 3v5h5"/><path d="M3.1 13a9 9 0 102.1-6.6L3 8"/><path d="M12 7v5l3 2"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  refresh: '<path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.5 9a9 9 0 0114.8-3.4L23 10M1 14l4.7 4.4A9 9 0 0020.5 15"/>',
};
const icon = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;

/* ================= Stare și API ================= */

const state = {
  month: shiftMonth(currentMonth(), -1),
  route: "dashboard",
  charts: [],
  categories: [],
  products: [],
  clients: [],
};

async function api(path, options = {}) {
  const opts = { credentials: "same-origin", headers: {}, ...options };
  if (opts.body && typeof opts.body !== "string" && !(opts.body instanceof FormData)) {
    opts.body = JSON.stringify(opts.body);
    opts.headers["Content-Type"] = "application/json";
  }
  const writes = opts.method && opts.method !== "GET";
  if (writes) setBusy(+1);
  let res;
  try {
    res = await fetch(path, opts);
  } catch {
    throw new Error("Nu mă pot conecta la aplicație. Verificați că fereastra pornită cu start.bat este deschisă.");
  } finally {
    if (writes) setBusy(-1);
  }
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    showAuth(true);
    throw new Error("Sesiunea a expirat. Autentificați-vă din nou.");
  }
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) {
    let msg = data?.detail || "A apărut o eroare.";
    if (Array.isArray(msg)) msg = msg.map((e) => e.msg.replace(/^Value error, /, "")).join(" ");
    throw new Error(msg);
  }
  return data;
}

// Cât timp se salvează ceva, formularele nu pot fi trimise a doua oară (de exemplu la dublu-click).
let pendingWrites = 0;
function setBusy(delta) {
  pendingWrites = Math.max(0, pendingWrites + delta);
  document.body.classList.toggle("busy", pendingWrites > 0);
  $$("form button[type=submit]").forEach((b) => { b.disabled = pendingWrites > 0; });
}
document.addEventListener("submit", (e) => {
  if (pendingWrites > 0) { e.preventDefault(); e.stopImmediatePropagation(); }
}, true);

function toast(message, type = "ok") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `${icon(type === "ok" ? "check" : "alert")}<span>${esc(message)}</span>`;
  $("#toasts").append(el);
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 300); }, 3200);
}

/* ================= Autentificare ================= */

let authMode = "login";

async function boot() {
  try {
    const status = await api("/api/auth/status");
    if (status.company) $("#brand-name").textContent = status.company;
    state.ownerName = status.owner_name;
    state.hasRecovery = status.has_recovery;
    if (status.logged_in) return showApp();
    authMode = status.setup_done ? "login" : "setup";
    showAuth();
  } catch (err) {
    toast(err.message, "err");
  }
}

const AUTH_TEXT = {
  setup: { title: "Bun venit la Testify Hardware", subtitle: "Prima pornire: alegeți o parolă. Doar dumneavoastră veți avea acces la aplicație.",
    label: "Parolă nouă", submit: "Creează parola și intră" },
  login: { title: "Bun venit înapoi", subtitle: "Introduceți parola ca să vedeți cifrele firmei.",
    label: "Parolă", submit: "Intră în aplicație", switchTo: "Am uitat parola" },
  recover: { title: "Ați uitat parola?", subtitle: "Introduceți codul de recuperare primit când ați creat parola și alegeți o parolă nouă.",
    label: "Parolă nouă", submit: "Schimbă parola și intră", switchTo: "Înapoi la autentificare" },
};

function showAuth(expired = false) {
  $("#app").classList.add("hidden");
  $("#auth-screen").classList.remove("hidden");
  $("#auth-form").classList.remove("hidden");
  $("#recovery-panel").classList.add("hidden");
  const text = AUTH_TEXT[authMode];
  const newPassword = authMode !== "login";
  $("#auth-title").textContent = text.title;
  $("#auth-subtitle").textContent = expired && authMode === "login" ? "Sesiunea a expirat. Introduceți parola din nou." : text.subtitle;
  $("#auth-password-label").textContent = text.label;
  $("#auth-code-wrap").classList.toggle("hidden", authMode !== "recover");
  $("#auth-code").required = authMode === "recover";
  $("#auth-confirm-wrap").classList.toggle("hidden", !newPassword);
  $("#auth-demo-wrap").classList.toggle("hidden", authMode !== "setup");
  $("#auth-submit").textContent = text.submit;
  $("#auth-switch").classList.toggle("hidden", !text.switchTo);
  $("#auth-switch").textContent = text.switchTo || "";
  $("#auth-password").autocomplete = newPassword ? "new-password" : "current-password";
  $("#auth-error").textContent = "";
  setTimeout(() => (authMode === "recover" ? $("#auth-code") : $("#auth-password")).focus(), 50);
}

$("#auth-switch").addEventListener("click", () => {
  authMode = authMode === "recover" ? "login" : "recover";
  showAuth();
});

$("#auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const password = $("#auth-password").value;
  const err = $("#auth-error");
  err.textContent = "";
  try {
    if (authMode !== "login" && password !== $("#auth-confirm").value) {
      err.textContent = "Parolele nu coincid.";
      return;
    }
    let result;
    if (authMode === "setup") {
      $("#auth-submit").textContent = "Se pregătește aplicația…";
      result = await api("/api/auth/setup", { method: "POST", body: { password, demo: $("#auth-demo").checked } });
    } else if (authMode === "recover") {
      result = await api("/api/auth/recover", { method: "POST", body: { code: $("#auth-code").value, password } });
    } else {
      result = await api("/api/auth/login", { method: "POST", body: { password } });
    }
    $("#auth-password").value = "";
    $("#auth-confirm").value = "";
    $("#auth-code").value = "";
    if (result.recovery_code) {
      // Codul nou se arată o singură dată, înainte de intrarea în aplicație.
      state.hasRecovery = true;
      $("#auth-form").classList.add("hidden");
      $("#auth-title").textContent = authMode === "setup" ? "Notați codul de recuperare" : "Parola a fost schimbată";
      $("#auth-subtitle").textContent = "Dacă vă uitați parola, cu acest cod vă puteți pune una nouă. Codul se arată acum o singură dată.";
      const panel = $("#recovery-panel");
      panel.classList.remove("hidden");
      mountRecoveryCode(panel, result.recovery_code, "Continuă în aplicație", () => { authMode = "login"; showApp(); });
      return;
    }
    showApp();
  } catch (ex) {
    err.textContent = ex.message;
    $("#auth-submit").textContent = AUTH_TEXT[authMode].submit;
  }
});

// Afișează codul de recuperare cu opțiuni de copiere, salvare și printare.
function mountRecoveryCode(root, code, continueLabel, onContinue) {
  root.innerHTML = `
    <div class="recovery-code" aria-label="Cod de recuperare">${esc(code)}</div>
    <div class="recovery-actions">
      <button class="btn btn-sm" type="button" data-act="copy">Copiază</button>
      <button class="btn btn-sm" type="button" data-act="save">Salvează ca fișier</button>
      <button class="btn btn-sm" type="button" data-act="print">Printează</button>
    </div>
    <p class="muted" style="font-size:12px;margin:0 0 12px">Păstrați-l pe hârtie sau într-un loc sigur, separat de calculator. După ce îl folosiți, primiți automat unul nou.</p>
    <label class="check"><input type="checkbox" data-act="ack"><span>Am notat codul într-un loc sigur</span></label>
    <button class="btn btn-primary btn-block" type="button" data-act="continue" disabled style="margin-top:14px">${esc(continueLabel)}</button>`;
  const text = `Testify Hardware — cod de recuperare a parolei\n\n${code}\n\nGenerat la ${new Date().toLocaleString("ro-RO")}.\nPăstrați acest cod într-un loc sigur.`;
  $("[data-act=copy]", root).onclick = async () => {
    try { await navigator.clipboard.writeText(code); toast("Codul a fost copiat."); }
    catch { toast("Copierea nu a mers. Notați codul de mână.", "err"); }
  };
  $("[data-act=save]", root).onclick = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    a.download = "testify-cod-recuperare.txt";
    a.click();
    URL.revokeObjectURL(a.href);
  };
  $("[data-act=print]", root).onclick = () => {
    const w = window.open("", "_blank", "width=480,height=360");
    if (!w) return;
    w.document.write(`<pre style="font:18px/1.6 monospace;padding:24px">${esc(text)}</pre>`);
    w.document.close();
    w.print();
  };
  $("[data-act=ack]", root).onchange = (e) => { $("[data-act=continue]", root).disabled = !e.target.checked; };
  $("[data-act=continue]", root).onclick = onContinue;
}

$("#logout-btn").addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" }).catch(() => {});
  $("#assistant").classList.add("hidden");
  robot.close();
  try { sessionStorage.removeItem("testi-greeted"); } catch { /* stocare indisponibilă */ }
  authMode = "login";
  showAuth();
});

/* ================= Navigare ================= */

const ROUTES = {
  dashboard: { label: "Dashboard", icon: "dashboard", eyebrow: "Imagine de ansamblu", title: "Cum merge firma", render: renderDashboard },
  vanzari: { label: "Vânzări", icon: "sales", eyebrow: "Facturi și încasări", title: "Vânzări", render: renderSales },
  stoc: { label: "Stoc", icon: "box", eyebrow: "Produse și inventar", title: "Produse și stoc", render: renderStock },
  clienti: { label: "Clienți", icon: "users", eyebrow: "Cine vă datorează bani", title: "Clienți și încasări", render: renderClients },
  furnizori: { label: "Furnizori", icon: "truck", eyebrow: "Cui datorați bani", title: "Furnizori și plăți", render: renderSuppliers },
  cheltuieli: { label: "Cheltuieli", icon: "expenses", eyebrow: "Bani care ies", title: "Cheltuieli", render: renderExpenses },
  bani: { label: "Trezorerie", icon: "bank", eyebrow: "Bani în cont", title: "Trezorerie și prognoză", render: renderTreasury, noMonth: true },
  angajati: { label: "Angajați", icon: "team", eyebrow: "Echipa și salariile", title: "Angajați", render: renderEmployees },
  taxe: { label: "Taxe", icon: "taxes", eyebrow: "Ce plătiți statului", title: "Taxe și contribuții", render: renderTaxes },
  calendar: { label: "Calendar fiscal", icon: "calendar", eyebrow: "Termene ANAF", title: "Calendar fiscal", render: renderCalendar, noMonth: true },
  rapoarte: { label: "Rapoarte", icon: "reports", eyebrow: "Pentru contabilă", title: "Rapoarte și export", render: renderReports },
  setari: { label: "Setări", icon: "settings", eyebrow: "Configurare", title: "Setări", render: renderSettings, noMonth: true },
};

function buildNav() {
  $("#nav").innerHTML = Object.entries(ROUTES).map(([key, r]) =>
    `<a class="nav-item" href="#${key}" data-route="${key}">${icon(r.icon)}<span>${r.label}</span></a>`).join("");
}

function showApp() {
  $("#auth-screen").classList.add("hidden");
  $("#app").classList.remove("hidden");
  buildNav();
  route();
  robot.init();
}

function route() {
  const key = location.hash.slice(1);
  const changed = state.route !== (ROUTES[key] ? key : "dashboard");
  state.route = ROUTES[key] ? key : "dashboard";
  if (changed) robot.close();  // panoul asistentului nu rămâne peste pagina nouă
  render();
}
window.addEventListener("hashchange", route);

function destroyCharts() {
  state.charts.forEach((c) => c.destroy());
  state.charts = [];
}

async function render() {
  const r = ROUTES[state.route];
  $$(".nav-item[data-route]").forEach((a) => a.classList.toggle("active", a.dataset.route === state.route));
  $("#page-title").textContent = r.title;
  $("#page-eyebrow").textContent = r.eyebrow;
  $("#month-picker").classList.toggle("hidden", !!r.noMonth);
  const inProgress = state.month === currentMonth();
  $("#month-label").textContent = monthLabel(state.month) + (inProgress ? " · în curs" : "");
  $("#month-next").disabled = state.month >= currentMonth();
  $("#month-next").style.opacity = state.month >= currentMonth() ? 0.3 : 1;
  destroyCharts();
  // Element nou la fiecare randare, ca să nu se adune event listener-ele vechi.
  const old = $("#view");
  const view = old.cloneNode(false);
  old.replaceWith(view);
  view.innerHTML = '<div class="grid kpis"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>';
  try {
    await r.render(view);
  } catch (err) {
    view.innerHTML = `<div class="card glass empty">${icon("alert")}<p>${esc(err.message)}</p></div>`;
  }
}

$("#month-prev").addEventListener("click", () => { state.month = shiftMonth(state.month, -1); render(); });
$("#month-next").addEventListener("click", () => {
  if (state.month < currentMonth()) { state.month = shiftMonth(state.month, 1); render(); }
});

function setMonthFromDate(iso) {
  const ym = iso.slice(0, 7);
  if (ym !== state.month) {
    state.month = ym;
    toast(`Am trecut la ${monthLabel(ym)}.`);
  }
}

/* ================= Modal ================= */

function openModal(title, html, onMount) {
  $("#modal-title").textContent = title;
  $("#modal-body").innerHTML = html;
  $("#modal").classList.remove("hidden");
  onMount?.($("#modal-body"));
  setTimeout(() => $("#modal-body input:not([type=hidden]), #modal-body select")?.focus(), 60);
}
function closeModal() { $("#modal").classList.add("hidden"); $("#modal-body").innerHTML = ""; }
$("#modal-close").addEventListener("click", closeModal);
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

function confirmBox(title, text, confirmLabel = "Șterge") {
  return new Promise((resolve) => {
    openModal(title, `
      <p class="muted">${esc(text)}</p>
      <div class="form-actions">
        <button class="btn btn-ghost" type="button" data-no>Renunță</button>
        <button class="btn btn-danger" type="button" data-yes>${icon(/^șterge/i.test(confirmLabel) ? "trash" : "check")}${esc(confirmLabel)}</button>
      </div>`, (body) => {
      $("[data-no]", body).onclick = () => { closeModal(); resolve(false); };
      $("[data-yes]", body).onclick = () => { closeModal(); resolve(true); };
    });
  });
}

function formData(form) {
  const data = {};
  for (const [k, v] of new FormData(form).entries()) data[k] = typeof v === "string" ? v.trim() : v;
  return data;
}

/* ================= Grafice ================= */

const hasChart = () => typeof window.Chart !== "undefined";
if (hasChart()) {
  Chart.defaults.color = "#8a99b4";
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.borderColor = "rgba(148,163,184,0.08)";
  Chart.defaults.plugins.tooltip.backgroundColor = "rgba(13,20,37,0.96)";
  Chart.defaults.plugins.tooltip.borderColor = "rgba(148,163,184,0.25)";
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.plugins.tooltip.cornerRadius = 10;
  Chart.defaults.plugins.tooltip.titleFont = { weight: "700" };
}

function gradient(ctx, area, from, to) {
  const g = ctx.createLinearGradient(0, area.top, 0, area.bottom);
  g.addColorStop(0, from);
  g.addColorStop(1, to);
  return g;
}

function makeChart(canvas, config) {
  if (!hasChart() || !canvas) return null;
  const chart = new Chart(canvas, config);
  state.charts.push(chart);
  return chart;
}

const moneyTick = (v) => (Math.abs(v) >= 1000 ? `${numberFmt.format(v / 1000)}k` : numberFmt.format(v));

function sparkline(values, color) {
  if (values.length < 2) return "";
  const w = 96, h = 36, pad = 3;
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => [pad + (i * (w - pad * 2)) / (values.length - 1), h - pad - ((v - min) / span) * (h - pad * 2)]);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const id = `sg${Math.random().toString(36).slice(2, 8)}`;
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".35"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
    <path d="${line} L${w - pad},${h} L${pad},${h} Z" fill="url(#${id})" stroke="none"/>
    <path d="${line}" stroke="${color}" stroke-width="2" fill="none"/>
    <circle cx="${pts.at(-1)[0]}" cy="${pts.at(-1)[1]}" r="2.8" fill="${color}" stroke="none"/></svg>`;
}

function countUp(el, target, suffix = " lei") {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const duration = 1100;
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 4);
    el.innerHTML = `${numberFmt.format(target * (reduce ? 1 : eased))}<small>${suffix}</small>`;
    if (t < 1 && !reduce) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function changeChip(value, invert = false) {
  if (value === null || value === undefined) return '<span class="chip">—</span>';
  const good = invert ? value <= 0 : value >= 0;
  return `<span class="chip ${good ? "up" : "down"}">${icon(value >= 0 ? "up" : "down")}${pct(Math.abs(value))}</span>`;
}

function animateBars(root) {
  requestAnimationFrame(() => $$(".bar i[data-w]", root).forEach((b) => { b.style.width = b.dataset.w; }));
}

/* ================= Dashboard ================= */

function greeting() {
  const h = new Date().getHours();
  return h < 11 ? "Bună dimineața" : h < 18 ? "Bună ziua" : "Bună seara";
}

async function renderDashboard(view) {
  const d = await api(`/api/dashboard?month=${state.month}`);
  const c = d.current;
  const trend = d.trend;
  const cmp = d.in_progress ? `vs. 1–${d.compared_until_day} luna trecută` : "vs. luna trecută";
  const r = d.receivables;

  const kpis = [
    { key: "revenue", label: "Venituri", icon: "coins", accent: "#22d3ee", value: c.revenue, spark: trend.map((t) => t.revenue), sub: `${c.sales_count} facturi · fără TVA` },
    { key: "gross_margin", label: "Marjă brută", icon: "box", accent: "#a78bfa", value: c.gross_margin, spark: trend.map((t) => t.gross_margin), sub: `${pct(c.gross_margin_pct)} din vânzări` },
    { key: "profit", label: "Profit net", icon: "profit", accent: c.profit >= 0 ? "#34d399" : "#f87171", value: c.profit, spark: trend.map((t) => t.profit), sub: `marjă netă ${pct(c.margin)}` },
    { key: "owner_income", label: "Îți rămâne ție", icon: "star", accent: "#fbbf24", value: c.owner_income, spark: trend.map((t) => Math.max(t.profit, 0)), sub: "după impozitul pe dividende" },
  ];
  const minis = [
    { label: "De încasat de la clienți", value: lei(r.total), note: r.overdue ? `${lei(r.overdue)} trecut de scadență` : "nimic restant", tone: r.overdue ? "warn" : "ok", href: "#clienti", icon: "wallet" },
    { label: "Valoarea stocului", value: lei(c.stock_value), note: d.low_stock.length ? `${d.low_stock.length} produse sub stocul minim` : "toate produsele pe stoc", tone: d.low_stock.length ? "warn" : "ok", href: "#stoc", icon: "box" },
    { label: c.vat_payer ? "TVA de plată" : "Taxe pe salarii", value: lei(c.vat_payer ? c.vat.payable : c.taxes.total - c.taxes.company_tax), note: c.vat_payer ? `colectată ${lei(c.vat.collected)} − deductibilă ${lei(c.vat.deductible)}` : "CAS, CASS, impozit, CAM", tone: "info", href: "#taxe", icon: "taxes" },
    { label: "De plătit furnizorilor", value: lei(d.payables.total), note: d.payables.due_soon ? `${lei(d.payables.due_soon)} scadent în 7 zile` : "nimic scadent săptămâna asta", tone: d.payables.overdue || d.payables.due_soon ? "warn" : "ok", href: "#furnizori", icon: "truck" },
  ];

  view.innerHTML = `
    <div class="hero">
      <h2>${greeting()}${d.owner_name ? `, ${esc(d.owner_name)}` : ""}! Iată cum arată <span>${esc(d.company)}</span> în ${esc(c.label)}.</h2>
      ${d.in_progress
        ? `<span class="badge"><span class="dot"></span>Lună în curs — date până azi</span>`
        : `<span class="chip up">${icon(d.closed ? "lock" : "check")}${d.closed ? "Lună închisă" : "Lună încheiată"}</span>`}
    </div>

    <section class="grid kpis">
      ${kpis.map((k) => `
        <article class="card glass kpi" style="--accent:${k.accent}">
          <div class="kpi-top">
            <span class="kpi-label"><span class="kpi-icon">${icon(k.icon)}</span>${k.label}</span>
            ${changeChip(d.changes[k.key], k.invert)}
          </div>
          <div class="kpi-value" data-count="${k.value}">0<small> lei</small></div>
          <div class="kpi-foot">
            <span class="sub">${esc(k.sub)}<br>${esc(cmp)}</span>
            ${sparkline(k.spark, k.accent)}
          </div>
        </article>`).join("")}
    </section>

    ${d.reminders?.length ? `<a class="reminder glass mt" href="#calendar">${robotSVG("mini")}<span><b>Testi îți amintește:</b> ${d.reminders.map((r) => `${esc(r.form)} — ${lei(r.amount)} până ${r.days_left === 0 ? "azi" : `pe ${formatDate(r.date).slice(0, 5)}`}`).join(" · ")}</span><span class="btn btn-sm">Vezi calendarul</span></a>` : ""}

    <section class="mini-kpis mt">
      ${minis.map((m) => `
        <a class="mini glass ${m.tone}" href="${m.href}">
          <span class="mini-ic">${icon(m.icon)}</span>
          <span class="mini-body"><span>${esc(m.label)}</span><strong>${m.value}</strong><small>${esc(m.note)}</small></span>
        </a>`).join("")}
    </section>

    ${goalsCard(d)}

    <section class="grid cols-2 mt">
      <article class="card glass fill">
        <div class="card-head">
          <div><h2>Evoluție lunară</h2><p>Venituri, marjă brută și profit net</p></div>
          <div class="stat-strip" style="grid-template-columns:repeat(2,auto);gap:18px">
            <div><span class="muted" style="font-size:12px">Venituri ${c.month.slice(0, 4)}</span><br><strong class="num">${lei(d.year.revenue)}</strong></div>
            <div><span class="muted" style="font-size:12px">Profit ${c.month.slice(0, 4)}</span><br><strong class="num" style="color:var(--green)">${lei(d.year.profit)}</strong></div>
          </div>
        </div>
        <div class="chart-box"><canvas id="trend-chart"></canvas></div>
      </article>

      <article class="card glass">
        <div class="card-head"><div><h2>Unde se duc banii</h2><p>Toate costurile din ${esc(c.label)}</p></div></div>
        ${d.flow.length ? `
        <div class="donut-wrap">
          <div class="donut"><canvas id="flow-chart"></canvas>
            <div class="donut-center"><span>Total costuri</span><strong class="num">${lei(d.flow.reduce((s, f) => s + f.amount, 0))}</strong></div>
          </div>
          <ul class="legend">
            ${d.flow.map((f) => `<li${f.details ? ` title="${esc(f.details.map((x) => `${x.name}: ${lei(x.amount)}`).join("\n"))}"` : ""}><span class="sw" style="background:${esc(f.color)}"></span><span>${esc(f.name)}</span><span class="val"><b>${pct(f.share)}</b> · ${lei(f.amount)}</span></li>`).join("")}
          </ul>
        </div>` : emptyState("Nu există încă costuri în această lună.")}
      </article>
    </section>

    <section class="grid cols-3 mt">
      <article class="card glass">
        <div class="card-head"><div><h2>Ce trebuie să știi</h2><p>Observații automate</p></div></div>
        ${d.insights.length ? `<ul class="insights">${d.insights.map((n, i) => `
          <li class="insight ${n.tone}" style="animation-delay:${i * 80}ms"><span class="ic">${icon(n.icon)}</span><span>${esc(n.text)}</span></li>`).join("")}</ul>`
          : emptyState("Adăugați vânzări și cheltuieli ca să apară observații.")}
      </article>

      <article class="card glass">
        <div class="card-head"><div><h2>Alerte</h2><p>Stoc și încasări</p></div></div>
        <ul class="insights">
          ${d.low_stock.slice(0, 4).map((p) => `
            <li class="insight ${p.status === "out" ? "bad" : "warn"}"><span class="ic">${icon("box")}</span>
              <span><b>${esc(p.name)}</b>: ${p.status === "out" ? "stoc epuizat" : `mai sunt ${p.stock} buc. (minim ${p.min_stock})`}. Comandă de la ${esc(p.supplier || "furnizor")}.</span></li>`).join("")}
          ${r.clients.filter((x) => x.overdue).slice(0, 3).map((x) => `
            <li class="insight bad"><span class="ic">${icon("wallet")}</span>
              <span><b>${esc(x.client)}</b> are ${lei(x.overdue)} trecuți de scadență.</span></li>`).join("")}
          ${d.payables.due_soon ? `<li class="insight warn"><span class="ic">${icon("truck")}</span><span>În următoarele 7 zile aveți de plătit <b>${lei(d.payables.due_soon)}</b> furnizorilor.</span></li>` : ""}
          ${!d.low_stock.length && !r.overdue && !d.payables.due_soon ? `<li class="insight good"><span class="ic">${icon("check")}</span><span>Nicio alertă. Stocul și încasările sunt în regulă.</span></li>` : ""}
        </ul>
      </article>

      <article class="card glass">
        <div class="card-head"><div><h2>Top clienți</h2><p>Vânzări în ${esc(c.label)}</p></div><a class="btn btn-sm" href="#clienti">Toți</a></div>
        ${d.top_clients.length ? `<div class="bars">${d.top_clients.map((x, i) => `
          <div class="bar-row"><header><span>${i + 1}. ${esc(x.client)} <span class="tag">${esc(x.type)}</span></span><span>${lei(x.amount)}</span></header>
          <div class="bar"><i data-w="${(x.amount / d.top_clients[0].amount) * 100}%" style="background:linear-gradient(90deg,#a78bfa,#22d3ee)"></i></div></div>`).join("")}</div>`
          : emptyState("Alegeți clientul la vânzări ca să vedeți topul.")}
      </article>
    </section>

    <section class="grid cols-2-even mt">
      <article class="card glass">
        <div class="card-head"><div><h2>Produsele care aduc cel mai mult profit</h2><p>Vânzări minus costul mărfii, în ${esc(c.label)}</p></div></div>
        ${d.top_products.length ? `<div class="bars">${d.top_products.map((p, i) => `
          <div class="bar-row"><header><span>${i + 1}. ${esc(p.product)}</span><span><b style="color:var(--green)">${lei(p.profit)}</b> din ${lei(p.amount)}</span></header>
          <div class="bar"><i data-w="${(p.profit / d.top_products[0].profit) * 100}%" style="background:linear-gradient(90deg,#3b82f6,#22d3ee)"></i></div>
          <small class="muted" style="font-size:12px">${numberFmt.format(p.quantity)} buc. vândute</small></div>`).join("")}</div>`
          : emptyState("Adăugați vânzări pe produse ca să vedeți topul.")}
      </article>
      <article class="card glass">
        <div class="card-head"><div><h2>Taxe luna aceasta</h2><p>Total fără TVA: <b style="color:var(--text)">${lei(c.taxes.total)}</b></p></div>
          <a class="btn btn-sm" href="#taxe">Detalii</a></div>
        <div class="bars">${taxBars(c.taxes, c.company_tax_label)}</div>
      </article>
    </section>`;

  $$("[data-count]", view).forEach((el) => countUp(el, Number(el.dataset.count)));
  animateBars(view);
  $("#goal-btn", view)?.addEventListener("click", () => openGoals(d.goals));

  makeChart($("#trend-chart"), {
    data: {
      labels: trend.map((t) => t.label),
      datasets: [
        { type: "line", label: "Profit net", data: trend.map((t) => t.profit), borderColor: "#fbbf24", backgroundColor: "#fbbf24",
          borderWidth: 3, tension: 0.4, pointRadius: 4, pointHoverRadius: 7, order: 0 },
        { type: "bar", label: "Venituri", data: trend.map((t) => t.revenue), borderRadius: 8, maxBarThickness: 34, order: 1,
          backgroundColor: (ctx) => ctx.chart.chartArea ? gradient(ctx.chart.ctx, ctx.chart.chartArea, "#22d3ee", "rgba(59,130,246,0.25)") : "#22d3ee" },
        { type: "bar", label: "Marjă brută", data: trend.map((t) => t.gross_margin), borderRadius: 8, maxBarThickness: 34, order: 2,
          backgroundColor: (ctx) => ctx.chart.chartArea ? gradient(ctx.chart.ctx, ctx.chart.chartArea, "rgba(167,139,250,0.9)", "rgba(167,139,250,0.15)") : "#a78bfa" },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      animation: { duration: 1200, easing: "easeOutQuart" },
      plugins: {
        legend: { position: "bottom", labels: { usePointStyle: true, pointStyle: "rectRounded", padding: 18 } },
        tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${lei(ctx.parsed.y)}` } },
      },
      scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { callback: moneyTick } } },
    },
  });

  makeChart($("#flow-chart"), {
    type: "doughnut",
    data: { labels: d.flow.map((f) => f.name), datasets: [{ data: d.flow.map((f) => f.amount), backgroundColor: d.flow.map((f) => f.color), borderColor: "#0d1425", borderWidth: 3, hoverOffset: 10 }] },
    options: {
      cutout: "72%", responsive: true, maintainAspectRatio: false, animation: { animateRotate: true, duration: 1300 },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${lei(ctx.parsed)}` } } },
    },
  });
}

function goalsCard(d) {
  const g = d.goals;
  if (!g) return `<section class="goal-cta glass mt"><span class="ic">${icon("target")}</span><span><b>Setați un obiectiv lunar</b> de vânzări și profit. Testi vă spune zilnic dacă îl atingeți.</span>
    <button class="btn btn-sm btn-gold" id="goal-btn" type="button">${icon("target")}Setează obiectiv</button></section>`;
  const row = (label, x, color) => {
    if (!x) return "";
    const ok = x.projected >= x.target;
    return `<div class="goal-row"><header><span>${label}</span><span><b>${lei(x.actual)}</b> din ${lei(x.target)} · <b style="color:${x.pct >= 100 ? "var(--green)" : "var(--text)"}">${pct(x.pct)}</b></span></header>
      <div class="bar goal-bar"><i data-w="${Math.min(Math.max(x.pct, 0), 100)}%" style="background:${color}"></i>${d.in_progress ? `<em style="left:${Math.min(Math.max(x.projected_pct, 0), 100)}%" title="Estimare la final de lună"></em>` : ""}</div>
      <small class="${ok ? "pos" : "neg"}">${d.in_progress ? (ok ? `În ritmul actual ajungeți la ${lei(x.projected)} — obiectiv atins.` : `În ritmul actual: ${lei(x.projected)}. Mai trebuie ~${lei(x.daily_needed)} pe zi.`) : (x.pct >= 100 ? "Obiectiv atins." : `Au lipsit ${lei(x.target - x.actual)}.`)}</small></div>`;
  };
  return `<section class="card glass mt goals">
    <div class="card-head"><div><h2>${icon("target")} Obiectivele lunii</h2><p>${d.in_progress ? `Ziua ${g.day} din ${g.days_in_month} · linia subțire arată estimarea la final de lună` : "Rezultatul final al lunii"}${g.specific ? "" : " · obiectiv general, pentru fiecare lună"}</p></div>
      <button class="btn btn-sm" id="goal-btn" type="button">${icon("edit")}Modifică</button></div>
    <div class="grid cols-2-even">${row("Vânzări (fără TVA)", g.revenue, "linear-gradient(90deg,#3b82f6,#22d3ee)")}${row("Profit net", g.profit, "linear-gradient(90deg,#34d399,#fbbf24)")}</div>
  </section>`;
}

async function openGoals() {
  const g = await api(`/api/goals?month=${state.month}`);
  const value = (o, k) => (o && o[k] != null ? o[k] : "");
  openModal("Obiective lunare", `<form id="goal-form">
    <p class="muted" style="margin-top:0">Obiectivul general se aplică în fiecare lună. Pentru o lună anume (de exemplu decembrie, cu sărbători) puteți pune altul. Lăsați gol ca să ștergeți.</p>
    <h3 style="font-size:14px;margin:10px 0">În fiecare lună</h3>
    <div class="form-grid">
      <label class="field"><span>Vânzări (lei, fără TVA)</span><input type="number" name="d_revenue" min="1" step="1" value="${value(g.default, "revenue")}"></label>
      <label class="field"><span>Profit net (lei)</span><input type="number" name="d_profit" step="1" value="${value(g.default, "profit")}"></label>
    </div>
    <h3 style="font-size:14px;margin:16px 0 10px">Doar pentru ${esc(monthLabel(state.month))}</h3>
    <div class="form-grid">
      <label class="field"><span>Vânzări (lei, fără TVA)</span><input type="number" name="m_revenue" min="1" step="1" value="${value(g.month, "revenue")}"></label>
      <label class="field"><span>Profit net (lei)</span><input type="number" name="m_profit" step="1" value="${value(g.month, "profit")}"></label>
    </div>
    <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
      <button class="btn btn-gold" type="submit">${icon("check")}Salvează</button></div></form>`, (body) => {
    $("#goal-form", body).addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const d = formData(ev.target);
      const num = (v) => (v === "" || v == null ? null : Number(v));
      try {
        await api("/api/goals", { method: "PUT", body: { month: "default", revenue: num(d.d_revenue), profit: num(d.d_profit) } });
        await api("/api/goals", { method: "PUT", body: { month: state.month, revenue: num(d.m_revenue), profit: num(d.m_profit) } });
        closeModal(); toast("Obiectivele au fost salvate."); render();
      } catch (err) { toast(err.message, "err"); }
    });
  });
}

/* ================= Trezorerie ================= */

async function renderTreasury(view) {
  let includeOverdue = false;
  try { includeOverdue = localStorage.getItem("testify-overdue") === "1"; } catch { /* stocare indisponibilă */ }
  const t = await api(`/api/treasury?include_overdue=${includeOverdue}`);
  const tone = t.goes_negative ? "bad" : t.lowest.balance < t.monthly_expenses ? "warn" : "good";
  view.innerHTML = `
    <section class="card glass balance-card">
      <div class="card-head"><div><h2>${icon("bank")} Câți bani aveți acum?</h2>
        <p>Introduceți soldul din bancă plus casa (numerarul). Aplicația nu vede contul bancar, așa că actualizați-l din când în când, ideal săptămânal.</p></div></div>
      <form id="balance-form" class="balance-form">
        <label class="field"><span>Sold bancă + casă azi (lei)</span><input type="number" name="balance" step="0.01" required value="${t.balance_set ? t.start_balance : ""}" placeholder="ex. 85000"></label>
        <button class="btn btn-primary" type="submit">${icon("check")}Actualizează</button>
        ${t.balance_date ? `<small class="${t.balance_stale ? "neg" : "muted"}">Ultima actualizare: ${formatDate(t.balance_date)}${t.balance_stale ? " — e mai veche de o săptămână" : ""}</small>` : ""}
      </form>
    </section>
    ${t.balance_set ? "" : `<div class="insight warn mt"><span class="ic">${icon("alert")}</span><span>Fără sold, prognoza pornește de la 0 lei și arată doar ce intră și ce iese.</span></div>`}

    <section class="grid kpis mt">
      <article class="card glass kpi" style="--accent:#22d3ee"><div class="kpi-top"><span class="kpi-label"><span class="kpi-icon">${icon("bank")}</span>Sold azi</span></div>
        <div class="kpi-value">${lei(t.start_balance)}</div><div class="kpi-foot"><span class="sub">bancă + casă</span></div></article>
      <article class="card glass kpi" style="--accent:#34d399"><div class="kpi-top"><span class="kpi-label"><span class="kpi-icon">${icon("down")}</span>Intră în 30 de zile</span></div>
        <div class="kpi-value">${lei(t.total_in)}</div><div class="kpi-foot"><span class="sub">încasări clienți + vânzări pe loc</span></div></article>
      <article class="card glass kpi" style="--accent:#f87171"><div class="kpi-top"><span class="kpi-label"><span class="kpi-icon">${icon("up")}</span>Iese în 30 de zile</span></div>
        <div class="kpi-value">${lei(t.total_out)}</div><div class="kpi-foot"><span class="sub">furnizori, cheltuieli, salarii, taxe</span></div></article>
      <article class="card glass kpi" style="--accent:${t.goes_negative ? "#f87171" : "#fbbf24"}"><div class="kpi-top"><span class="kpi-label"><span class="kpi-icon">${icon("alert")}</span>Cel mai mic sold</span></div>
        <div class="kpi-value" style="color:${t.goes_negative ? "var(--red)" : "inherit"}">${lei(t.lowest.balance)}</div><div class="kpi-foot"><span class="sub">pe ${formatDate(t.lowest.date)}</span></div></article>
    </section>

    <div class="insight ${tone} mt"><span class="ic">${icon(tone === "good" ? "check" : "alert")}</span><span>${t.goes_negative
      ? `Atenție: pe <b>${formatDate(t.lowest.date)}</b> contul ar ajunge pe minus (<b>${lei(t.lowest.balance)}</b>). Grăbiți încasările restante (${lei(t.overdue_receivables)}) sau amânați o plată.`
      : tone === "warn" ? `Soldul scade până la <b>${lei(t.lowest.balance)}</b> pe ${formatDate(t.lowest.date)}, mai puțin decât cheltuielile obișnuite ale unei luni (${lei(t.monthly_expenses)}). Fiți atent la plăți mari.`
      : `Banii ajung pentru toate plățile din următoarele 30 de zile. Peste 30 de zile veți avea aproximativ <b>${lei(t.end_balance)}</b>.`}</span></div>

    <section class="card glass mt">
      <div class="card-head"><div><h2>Soldul zi de zi</h2><p>Următoarele 30 de zile, cu TVA inclus (exact cum se mișcă banii în cont)</p></div>
        <label class="check"><input type="checkbox" id="include-overdue" ${t.include_overdue ? "checked" : ""}><span>Socotește și restanțele clienților (${lei(t.overdue_receivables)}) ca încasate în 7 zile</span></label></div>
      <div class="chart-box"><canvas id="cash-chart"></canvas></div>
    </section>

    <section class="grid cols-2-even mt" style="align-items:start">
      <article class="card glass">
        <div class="card-head"><div><h2>Ce intră și ce iese</h2><p>Plățile și încasările cu dată sigură</p></div></div>
        ${t.events.length ? `<div class="table-wrap events-list"><table class="compact"><tbody>${t.events.map((e) => `<tr><td style="white-space:nowrap">${formatDate(e.date).slice(0, 5)}</td>
          <td>${esc(e.label)}</td><td class="r" style="color:${e.amount > 0 ? "var(--green)" : "var(--red)"};font-weight:700;white-space:nowrap">${e.amount > 0 ? "+" : "−"}${lei(Math.abs(e.amount))}</td></tr>`).join("")}</tbody></table></div>`
          : emptyState("Nicio plată sau încasare programată.")}
      </article>
      <article class="card glass">
        <div class="card-head"><div><h2>Cum se calculează</h2><p>Estimări din datele de până acum</p></div></div>
        <ul class="insights">
          <li class="insight info"><span class="ic">${icon("wallet")}</span><span>Facturile neîncasate intră la scadență (cu TVA).</span></li>
          <li class="insight info"><span class="ic">${icon("sales")}</span><span>Vânzări plătite pe loc: cam <b>${lei(t.daily_cash_sales)}</b> pe zi (media ultimelor 90 de zile).</span></li>
          <li class="insight info"><span class="ic">${icon("expenses")}</span><span>Cheltuieli obișnuite: cam <b>${lei(t.monthly_expenses)}</b> pe lună (media ultimelor 3 luni), împărțite pe zile.</span></li>
          <li class="insight info"><span class="ic">${icon("truck")}</span><span>Marfa de la furnizori se plătește la scadență; restanțele, imediat.</span></li>
          <li class="insight info"><span class="ic">${icon("calendar")}</span><span>Salariile, taxele pe salarii, TVA și impozitul pe profit, la termenele din Calendarul fiscal.</span></li>
        </ul>
      </article>
    </section>`;

  $("#balance-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await api("/api/treasury/balance", { method: "PUT", body: { balance: Number(formData(e.target).balance) } }); toast("Soldul a fost actualizat."); render(); }
    catch (err) { toast(err.message, "err"); }
  });
  $("#include-overdue").addEventListener("change", (e) => {
    try { localStorage.setItem("testify-overdue", e.target.checked ? "1" : "0"); } catch { /* stocare indisponibilă */ }
    render();
  });
  makeChart($("#cash-chart"), {
    type: "line",
    data: {
      labels: t.days.map((x) => formatDate(x.date).slice(0, 5)),
      datasets: [{ label: "Sold estimat", data: t.days.map((x) => x.balance), borderColor: "#22d3ee", borderWidth: 3, tension: 0.3, pointRadius: 0, pointHoverRadius: 6,
        fill: { target: { value: 0 }, above: "rgba(34,211,238,0.12)", below: "rgba(248,113,113,0.25)" } }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => ` Sold: ${lei(ctx.parsed.y)}`,
        afterLabel: (ctx) => { const day = t.days[ctx.dataIndex]; return ` +${lei(day.in)} / −${lei(day.out)}`; } } } },
      scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } }, y: { ticks: { callback: moneyTick } } },
    },
  });
}

/* ================= Calendar fiscal ================= */

const OBLIGATION_STATUS = { soon: "în curând", upcoming: "urmează", past: "termen trecut", paid: "plătit" };

async function renderCalendar(view) {
  const year = Number(state.month.slice(0, 4));
  const d = await api(`/api/obligations?year=${year}`);
  const items = d.items;
  const upcoming = items.filter((i) => ["soon", "upcoming"].includes(i.status));
  const next = upcoming.find((i) => i.kind === "anaf" && i.amount > 0);
  const nextDate = next?.date;
  const nextTotal = items.filter((i) => i.date === nextDate && i.kind !== "info" && !i.paid && i.amount > 0).reduce((s, i) => s + i.amount, 0);
  const pt = d.profit_tax;
  const groups = {};
  items.forEach((i) => (groups[i.date] ||= []).push(i));

  view.innerHTML = `
    ${next ? `<section class="card glass next-deadline">
      <div class="nd-date"><span>${formatDate(nextDate).slice(0, 5)}</span><small>${next.days_left === 0 ? "azi" : `în ${next.days_left} zile`}</small></div>
      <div><h2>Următorul termen la ANAF</h2><p>De plătit în total: <b class="num" style="font-size:22px;color:var(--gold)">${lei(nextTotal)}</b></p>
        <p class="muted" style="margin:4px 0 0">Termenele care pică în weekend sau de sărbători sunt mutate automat în prima zi lucrătoare.</p></div>
    </section>` : ""}

    <section class="grid cols-2 mt" style="align-items:start">
      <article class="card glass">
        <div class="card-head"><div><h2>Termene și sume</h2><p>Sumele lunii în curs sunt estimări și se actualizează pe măsură ce introduceți date. Bifați „Am plătit” ca Testi să nu vă mai amintească.</p></div></div>
        <div class="deadlines">${Object.entries(groups).map(([date, list]) => `
          <div class="dl-day ${list.every((i) => ["past", "paid"].includes(i.status)) ? "done" : ""}">
            <div class="dl-date"><b>${formatDate(date).slice(0, 5)}</b><small>${new Date(date + "T12:00").toLocaleDateString("ro-RO", { weekday: "short" })}</small></div>
            <ul>${list.map((i) => `<li class="dl-item ${i.status}">
              <span class="tag form-tag">${esc(i.form)}</span>
              <span class="dl-title">${esc(i.title)}${i.estimate ? ' <span class="tag">estimat</span>' : ""}${i.details ? `<small>${esc(i.details)}</small>` : ""}</span>
              <span class="dl-amount">${i.amount == null ? "" : `<b class="${i.amount < 0 ? "pos" : ""}">${i.amount < 0 ? "+" : ""}${lei(Math.abs(i.amount))}</b>`}</span>
              ${i.kind !== "info" && i.amount > 0 && i.status !== "past" ? `<button class="tag ${i.paid ? "paid" : "unpaid"}" data-ob="${esc(i.id)}" data-value="${i.paid ? 0 : 1}">${i.paid ? `${icon("check")}Plătit` : "Am plătit"}</button>` : `<span class="tag muted-tag">${OBLIGATION_STATUS[i.status]}</span>`}
            </li>`).join("")}</ul>
          </div>`).join("")}</div>
      </article>

      <article class="card glass">
        <div class="card-head"><div><h2>Impozit pe profit ${year}</h2><p>Se plătește trimestrial, din profitul cumulat de la începutul anului. Pierderile se recuperează din cel mult ${pct(pt.loss_limit_pct)} din profit.</p></div></div>
        ${d.regime === "micro" ? `<p class="muted">Firma este setată ca microîntreprindere: impozitul se plătește din venituri, vezi termenele din stânga.</p>` : `
        <div class="table-wrap"><table class="compact">
          <thead><tr><th>Trim.</th><th class="r">Profit</th><th class="r">Cumulat</th><th class="r" title="Pierdere fiscală recuperată">Pierdere</th><th class="r">De plată</th></tr></thead>
          <tbody>${pt.quarters.map((q) => `<tr><td><b>T${q.quarter}</b><br><small class="muted">până ${formatDate(q.deadline).slice(0, 5)}${q.quarter === 4 ? ` ${q.deadline.slice(0, 4)}` : ""}</small></td>
            <td class="r" style="color:${q.profit_before_tax < 0 ? "var(--red)" : "inherit"}">${lei(q.profit_before_tax)}</td><td class="r">${lei(q.cumulative_pbt)}</td>
            <td class="r">${q.loss_recovered ? lei(q.loss_recovered) : "—"}</td>
            <td class="r"><b style="color:var(--gold)">${lei(q.tax_due)}</b>${q.estimate ? '<br><small class="muted">estimat</small>' : ""}</td></tr>`).join("")}</tbody>
          <tfoot><tr><td colspan="4">Total ${year}</td><td class="r">${lei(pt.total)}</td></tr></tfoot>
        </table></div>
        <ul class="insights mt">
          <li class="insight info"><span class="ic">${icon("percent")}</span><span>Pierdere fiscală de recuperat la începutul lui ${year}: <b>${lei(pt.loss_at_start)}</b>. Pierderile din anii dinaintea aplicației se trec în Setări.</span></li>
          <li class="insight info"><span class="ic">${icon("alert")}</span><span>Lunar, rapoartele arată impozitul ca la contabil (16% din profitul lunii). Aici e suma care se plătește efectiv: o lună pe pierdere scade impozitul trimestrului.</span></li>
        </ul>`}
      </article>
    </section>`;

  view.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-ob]");
    if (!btn) return;
    try {
      await api(`/api/obligations/${btn.dataset.ob}/paid`, { method: "PATCH", body: { paid: btn.dataset.value === "1" } });
      toast(btn.dataset.value === "1" ? "Notat ca plătit. Testi nu vă mai amintește de el." : "Bifa a fost scoasă.");
      render();
    } catch (err) { toast(err.message, "err"); }
  });
}

function taxBars(t, companyLabel) {
  const items = [
    ["CAS — pensii", t.cas, "#a78bfa"], ["CASS — sănătate", t.cass, "#34d399"],
    ["Impozit pe salarii", t.income_tax, "#22d3ee"], ["CAM — contribuția firmei", t.cam, "#fb923c"],
    [companyLabel, t.company_tax, "#fbbf24"],
  ];
  const max = Math.max(...items.map((i) => i[1]), 1);
  return items.map(([name, value, color]) => `
    <div class="bar-row"><header><span>${name}</span><span>${lei(value)}</span></header>
    <div class="bar"><i data-w="${(value / max) * 100}%" style="background:${color}"></i></div></div>`).join("");
}

/* Tabelele lungi afișează 25 de rânduri, cu „Arată mai multe” și căutare. */
function paginate(view, rowsSel, searchSel, pageSize = 25) {
  const tbody = $(rowsSel, view);
  if (!tbody) return;
  let limit = pageSize;
  const more = document.createElement("div");
  more.className = "more";
  tbody.closest(".table-wrap").after(more);
  const apply = () => {
    const q = ($(searchSel, view)?.value || "").toLowerCase();
    const matches = $$("tr", tbody).filter((tr) => tr.dataset.search.includes(q));
    $$("tr", tbody).forEach((tr) => { tr.style.display = "none"; });
    matches.slice(0, limit).forEach((tr) => { tr.style.display = ""; });
    const rest = matches.length - limit;
    more.innerHTML = rest > 0
      ? `<button class="btn btn-sm" type="button">Arată mai multe (${rest} rămase)</button>` : "";
    $("button", more)?.addEventListener("click", () => { limit += 50; apply(); });
  };
  $(searchSel, view)?.addEventListener("input", () => { limit = pageSize; apply(); });
  apply();
}

function emptyState(text) {
  return `<div class="empty">${icon("box")}<p>${esc(text)}</p></div>`;
}

/* ================= Vânzări ================= */

let saleMode = "order";

// Produsele și clienții, pentru listele din formulare.
async function loadCatalog() {
  const [products, clients] = await Promise.all([api("/api/products"), api("/api/clients")]);
  state.products = products;
  state.clients = clients;
}

// Data propusă e mereu azi; după salvare, aplicația trece la luna înregistrării.
function defaultDate() {
  return todayISO();
}

function clientOptions(selected) {
  const fallback = state.clients.find((c) => c.name === "Persoana fizica")?.id;
  const value = selected ?? fallback;
  return `<option value="">— fără client —</option>` + state.clients.map((c) =>
    `<option value="${c.id}" ${c.id === value ? "selected" : ""}>${esc(c.name)}${c.payment_terms ? ` · plată la ${c.payment_terms} zile` : ""}</option>`).join("");
}

function productOptions(selected) {
  return `<option value="">Alegeți produsul…</option>` + state.products.filter((p) => p.active || p.id === selected).map((p) =>
    `<option value="${p.id}" ${p.id === selected ? "selected" : ""}>${esc(p.code)} · ${esc(p.name)} — ${p.stock} buc.</option>`).join("");
}

function saleFormHTML(sale = {}, mode = "order") {
  const isOrder = mode === "order";
  return `
    <div class="form-grid">
      <label class="field"><span>Data</span><input type="date" name="date" required value="${esc(sale.date || defaultDate())}"></label>
      <label class="field" style="grid-column:span 2"><span>Client</span><select name="client_id">${clientOptions(sale.client_id)}</select></label>
      ${isOrder ? `
        <label class="field" style="grid-column:1/-1"><span>Produs</span><select name="product_id" required>${productOptions(sale.product_id)}</select></label>
        <label class="field"><span>Cantitate</span><input type="number" name="quantity" min="1" step="1" required value="${esc(sale.quantity || 1)}"></label>
        <label class="field"><span>Preț / buc. fără TVA</span><input type="number" name="unit_price" min="0.01" step="0.01" placeholder="din fișa produsului" value="${esc(sale.unit_price ?? "")}"></label>
        <label class="field"><span>Reducere (%)</span><input type="number" name="discount" min="0" max="99" step="0.5" placeholder="0" value="${esc(sale.discount || "")}"></label>
        <div class="sale-calc" style="grid-column:1/-1"></div>
      ` : `
        <label class="field" style="grid-column:span 2"><span>Descriere</span><input name="description" required maxlength="200" placeholder="ex. Vânzări magazin — total zi" value="${esc(sale.description || "")}"></label>
        <label class="field"><span>Sumă fără TVA (lei)</span><input type="number" name="amount" min="0.01" step="0.01" required placeholder="0,00" value="${esc(sale.amount ?? "")}"></label>
        <label class="field"><span>Costul mărfii (opțional)</span><input type="number" name="cost_total" min="0" step="0.01" placeholder="0,00" value="${esc(sale.unit_cost ?? "")}"><small>Pentru o marjă corectă.</small></label>
      `}
    </div>`;
}

// La comandă: prețul vine din fișa produsului, iar dedesubt se văd totalul, stocul și profitul.
function wireSaleForm(form) {
  const select = $("[name=product_id]", form);
  if (!select) return;
  const qty = $("[name=quantity]", form), price = $("[name=unit_price]", form), out = $(".sale-calc", form);
  const discount = $("[name=discount]", form);
  const update = (fromProduct) => {
    const p = state.products.find((x) => x.id === Number(select.value));
    if (!p) { out.innerHTML = ""; return; }
    if (fromProduct || !price.value) price.value = p.sale_price ? p.sale_price.toFixed(2) : "";
    const q = Number(qty.value) || 0, u = Number(price.value) || 0, d = Math.min(Number(discount.value) || 0, 99);
    const total = q * u * (1 - d / 100), profit = total - q * p.cost;
    const after = p.stock - q;
    out.innerHTML = `
      <span>Total: <b>${lei(total, true)}</b>${d ? ` <small class="muted">(reducere ${pct(d)}: −${lei(q * u - total, true)})</small>` : ""}</span>
      <span>Profit din vânzare: <b style="color:${profit >= 0 ? "var(--green)" : "var(--red)"}">${lei(profit, true)}</b></span>
      <span class="${after < 0 ? "neg" : after <= p.min_stock ? "warn" : ""}">Stoc după vânzare: <b>${after} buc.</b>${after < 0 ? " — stoc insuficient!" : after <= p.min_stock ? " — sub minim" : ""}</span>`;
  };
  select.addEventListener("change", () => update(true));
  qty.addEventListener("input", () => update(false));
  price.addEventListener("input", () => update(false));
  discount.addEventListener("input", () => update(false));
  update(false);
}

function salePayload(form, mode) {
  const d = formData(form);
  const payload = { date: d.date, client_id: d.client_id ? Number(d.client_id) : null };
  if (mode === "order") {
    payload.product_id = Number(d.product_id);
    payload.quantity = Number(d.quantity) || 1;
    if (d.unit_price) payload.unit_price = Number(d.unit_price);
    payload.discount = Number(d.discount) || 0;
  } else {
    payload.description = d.description;
    payload.amount = Number(d.amount);
    payload.cost_total = d.cost_total ? Number(d.cost_total) : null;
  }
  return payload;
}

function paidChip(s) {
  if (s.amount < 0) return `<span class="tag storno">Retur${s.storno_of_invoice ? ` la ${esc(s.storno_of_invoice)}` : ""}</span>`;
  if (s.paid) return `<button class="tag paid" data-paid="${s.id}" data-value="0" title="Marchează ca neîncasată">${icon("check")}Încasat</button>`;
  const late = s.due_date && s.due_date < todayISO();
  return `<button class="tag ${late ? "late" : "unpaid"}" data-paid="${s.id}" data-value="1" title="Marchează ca încasată">${late ? "Restantă" : "Neîncasat"} · ${formatDate(s.due_date).slice(0, 5)}</button>`;
}

async function saveSale(payload, id) {
  const result = await api(id ? `/api/sales/${id}` : "/api/sales", { method: id ? "PUT" : "POST", body: payload });
  if (result.warning) toast(result.warning, "err");
  return result;
}

async function renderSales(view) {
  const [sales] = await Promise.all([api(`/api/sales?month=${state.month}`), loadCatalog()]);
  const total = sales.reduce((s, x) => s + x.amount, 0);
  const margin = sales.reduce((s, x) => s + x.amount - (x.quantity || 1) * (x.unit_cost || 0), 0);
  const unpaid = sales.filter((s) => !s.paid).reduce((s, x) => s + x.amount, 0);
  const invoices = sales.filter((s) => s.invoice_number).length;

  view.innerHTML = `
    <section class="card glass">
      <div class="card-head">
        <div><h2>Factură nouă</h2><p>Alegeți produsul din stoc, sau introduceți doar totalul pe zi/lună.</p></div>
        <div class="segmented" id="sale-mode">
          <button type="button" data-mode="order" class="${saleMode === "order" ? "active" : ""}">Produs din stoc</button>
          <button type="button" data-mode="total" class="${saleMode === "total" ? "active" : ""}">Total zi / lună</button>
        </div>
      </div>
      <form id="sale-form">
        <div id="sale-fields">${saleFormHTML({}, saleMode)}</div>
        <div class="form-actions"><button class="btn btn-primary" type="submit">${icon("plus")}Emite factura</button></div>
      </form>
    </section>

    <section class="stat-strip mt">
      <div class="stat"><span>Vânzări fără TVA</span><strong>${lei(total)}</strong></div>
      <div class="stat"><span>Facturi emise</span><strong>${invoices}</strong></div>
      <div class="stat"><span>Marjă brută</span><strong style="color:var(--green)">${lei(margin)} <small class="muted">${total ? pct((margin / total) * 100) : ""}</small></strong></div>
      <div class="stat"><span>Neîncasat din luna aceasta</span><strong style="color:${unpaid ? "var(--gold)" : "inherit"}">${lei(unpaid)}</strong></div>
    </section>

    <section class="card glass mt">
      <div class="card-head">
        <div><h2>Vânzări — ${esc(monthLabel(state.month))}</h2><p>Apăsați pe status ca să marcați o factură încasată.</p></div>
        <div class="toolbar"><label class="field search">${icon("search")}<input id="sale-search" placeholder="Caută factură, client sau produs…"></label></div>
      </div>
      ${sales.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Data</th><th>Factură</th><th>Client</th><th>Produs / descriere</th><th class="r">Cant.</th><th class="r">Valoare</th><th>Status</th><th></th></tr></thead>
        <tbody id="sale-rows">${sales.map((s) => `
          <tr data-search="${esc(`${s.invoice_number || ""} ${s.client_name || ""} ${s.description} ${s.product || ""}`.toLowerCase())}">
            <td>${formatDate(s.date)}</td>
            <td class="mono">${esc(s.invoice_number || "—")}</td>
            <td>${esc(s.client_name || "—")}</td>
            <td>${esc(s.amount < 0 ? s.description : s.product || s.description)}${s.product_id || s.amount < 0 ? "" : ' <span class="tag total">Total</span>'}${s.discount ? ` <span class="tag">−${pct(s.discount)}</span>` : ""}${s.returned_amount ? ` <span class="tag storno" title="Retur de ${lei(s.returned_amount, true)}">returnat ${s.returned_quantity ? `${s.returned_quantity} buc.` : lei(s.returned_amount)}</span>` : ""}</td>
            <td class="r">${s.quantity ?? "—"}</td>
            <td class="r"><b class="${s.amount < 0 ? "neg" : ""}">${lei(s.amount, true)}</b></td>
            <td>${paidChip(s)}</td>
            <td class="actions">
              ${s.amount > 0 && !(s.returned_amount >= s.amount - 0.001) ? `<button class="icon-btn" data-return="${s.id}" title="Retur / stornare">${icon("undo")}</button>` : ""}
              ${s.amount > 0 && !s.returned_amount ? `<button class="icon-btn" data-edit="${s.id}" title="Editează">${icon("edit")}</button>` : ""}
              <button class="icon-btn danger" data-del="${s.id}" title="Șterge">${icon("trash")}</button>
            </td>
          </tr>`).join("")}</tbody>
        <tfoot><tr><td colspan="5">Total lună</td><td class="r">${lei(total, true)}</td><td colspan="2"></td></tr></tfoot>
      </table></div>` : emptyState("Nu există vânzări în această lună. Emiteți prima factură mai sus.")}
    </section>`;

  const form = $("#sale-form");
  wireSaleForm(form);
  $$("#sale-mode button").forEach((b) => b.addEventListener("click", () => {
    saleMode = b.dataset.mode;
    $$("#sale-mode button").forEach((x) => x.classList.toggle("active", x === b));
    $("#sale-fields").innerHTML = saleFormHTML({ date: $("[name=date]", form).value }, saleMode);
    wireSaleForm(form);
  }));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const payload = salePayload(form, saleMode);
      const result = await saveSale(payload);
      toast(`Factura ${result.invoice_number} a fost emisă.`);
      setMonthFromDate(payload.date);
      render();
    } catch (err) { toast(err.message, "err"); }
  });

  paginate(view, "#sale-rows", "#sale-search");

  view.addEventListener("click", async (e) => {
    const edit = e.target.closest("[data-edit]"), del = e.target.closest("[data-del]"), paid = e.target.closest("[data-paid]");
    const ret = e.target.closest("[data-return]");
    if (ret) openReturn(sales.find((s) => s.id === Number(ret.dataset.return)));
    if (paid) {
      try {
        await api(`/api/sales/${paid.dataset.paid}/paid`, { method: "PATCH", body: { paid: paid.dataset.value === "1" } });
        toast(paid.dataset.value === "1" ? "Factura a fost marcată încasată." : "Factura a fost marcată neîncasată.");
        render();
      } catch (err) { toast(err.message, "err"); }
    }
    if (edit) {
      const sale = sales.find((s) => s.id === Number(edit.dataset.edit));
      const mode = sale.product_id ? "order" : "total";
      openModal(`Editează ${sale.invoice_number || "vânzarea"}`, `<form id="edit-sale">${saleFormHTML(sale, mode)}
        <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
        <button class="btn btn-primary" type="submit">${icon("check")}Salvează</button></div></form>`, (body) => {
        const f = $("#edit-sale", body);
        wireSaleForm(f);
        f.addEventListener("submit", async (ev) => {
          ev.preventDefault();
          try {
            const payload = { ...salePayload(f, mode), paid: Boolean(sale.paid), invoice_number: sale.invoice_number };
            await saveSale(payload, sale.id);
            closeModal(); toast("Vânzarea a fost actualizată."); setMonthFromDate(payload.date); render();
          } catch (err) { toast(err.message, "err"); }
        });
      });
    }
    if (del && await confirmBox("Ștergeți vânzarea?", "Vânzarea va fi ștearsă definitiv, iar marfa revine în stoc.")) {
      try { await api(`/api/sales/${del.dataset.del}`, { method: "DELETE" }); toast("Vânzarea a fost ștearsă."); render(); }
      catch (err) { toast(err.message, "err"); }
    }
  });
}

// Retur: factură de stornare (cu minus). Marfa revine în stoc, venitul și TVA scad.
function openReturn(sale) {
  const isProduct = !!sale.product_id;
  const left = isProduct ? sale.quantity - (sale.returned_quantity || 0) : +(sale.amount - (sale.returned_amount || 0)).toFixed(2);
  openModal(`Retur la factura ${esc(sale.invoice_number || "")}`, `<form id="return-form">
    <p class="muted" style="margin-top:0">Se emite o factură de stornare (cu minus), legată de ${esc(sale.invoice_number || "factură")}.
      ${isProduct ? "Marfa returnată revine în stoc." : ""} Venitul, TVA și profitul scad în luna returului.</p>
    <div class="form-grid">
      <label class="field"><span>Data returului</span><input type="date" name="date" required value="${todayISO()}" min="${esc(sale.date)}" max="${todayISO()}"></label>
      ${isProduct
        ? `<label class="field"><span>Bucăți returnate (din ${left})</span><input type="number" name="quantity" min="1" max="${left}" step="1" required value="${left}"></label>`
        : `<label class="field"><span>Suma stornată, fără TVA (max. ${lei(left, true)})</span><input type="number" name="amount" min="0.01" max="${left}" step="0.01" required value="${left}"></label>`}
      <label class="field" style="grid-column:1/-1"><span>Motiv (opțional)</span><input name="reason" maxlength="200" placeholder="ex. produs defect, comandă anulată"></label>
    </div>
    <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
      <button class="btn btn-primary" type="submit">${icon("undo")}Emite stornarea</button></div></form>`, (body) => {
    $("#return-form", body).addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const d = formData(ev.target);
      const payload = { date: d.date, reason: d.reason };
      if (isProduct) payload.quantity = Number(d.quantity); else payload.amount = Number(d.amount);
      try {
        const result = await api(`/api/sales/${sale.id}/return`, { method: "POST", body: payload });
        closeModal(); toast(`Stornarea ${result.invoice_number} a fost emisă (${lei(result.amount, true)}).`);
        setMonthFromDate(payload.date); render();
      } catch (err) { toast(err.message, "err"); }
    });
  });
}

/* ================= Stoc ================= */

let stockTab = "products";

function productFormHTML(p = {}) {
  return `
    <div class="form-grid">
      <label class="field"><span>Cod</span><input name="code" required maxlength="40" value="${esc(p.code || "")}" placeholder="ex. P115"></label>
      <label class="field" style="grid-column:span 2"><span>Denumire</span><input name="name" required maxlength="200" value="${esc(p.name || "")}"></label>
      <label class="field"><span>Categorie</span><input name="category" maxlength="100" value="${esc(p.category || "")}" placeholder="ex. Periferice"></label>
      <label class="field" style="grid-column:span 2"><span>Furnizor</span><input name="supplier" maxlength="120" value="${esc(p.supplier || "")}"></label>
      <label class="field"><span>Preț vânzare fără TVA</span><input type="number" name="sale_price" min="0" step="0.01" required value="${esc(p.sale_price ?? "")}"></label>
      <label class="field"><span>Cost achiziție</span><input type="number" name="cost" min="0" step="0.01" required value="${esc(p.cost ?? "")}"></label>
      <label class="field"><span>Stoc minim</span><input type="number" name="min_stock" min="0" step="1" value="${esc(p.min_stock ?? 5)}"><small>Sub el primiți alertă.</small></label>
      ${p.id ? "" : `<label class="field"><span>Stoc actual</span><input type="number" name="opening_stock" min="0" step="1" value="0"></label>`}
    </div>`;
}

function productPayload(form) {
  const d = formData(form);
  return { code: d.code, name: d.name, category: d.category, supplier: d.supplier,
    sale_price: Number(d.sale_price), cost: Number(d.cost), min_stock: Number(d.min_stock) || 0,
    opening_stock: Number(d.opening_stock) || 0, active: true };
}

function openReceive(productId) {
  const p = state.products.find((x) => x.id === productId);
  openModal("Recepție marfă (NIR)", `<form id="nir-form">
    <div class="form-grid">
      <label class="field" style="grid-column:1/-1"><span>Produs</span><select name="product_id" required>${productOptions(productId)}</select></label>
      <label class="field"><span>Data</span><input type="date" name="date" required value="${todayISO()}"></label>
      <label class="field"><span>Cantitate primită</span><input type="number" name="quantity" min="1" step="1" required value="${p ? Math.max(p.min_stock * 2 - p.stock, 1) : 1}"></label>
      <label class="field"><span>Cost / buc. fără TVA</span><input type="number" name="unit_cost" min="0.01" step="0.01" value="${p ? p.cost : ""}"></label>
      <label class="field" style="grid-column:span 2"><span>Furnizor</span><input name="supplier" maxlength="120" value="${esc(p?.supplier || "")}"></label>
      <label class="field"><span>Nr. NIR (opțional)</span><input name="doc_number" maxlength="40" placeholder="automat"></label>
    </div>
    <p class="muted" style="font-size:13px">Stocul crește imediat. Costul mărfii intră în profit abia când marfa se vinde.</p>
    <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
    <button class="btn btn-primary" type="submit">${icon("check")}Adaugă în stoc</button></div></form>`, (body) => {
    $("#nir-form", body).addEventListener("submit", async (e) => {
      e.preventDefault();
      const d = formData(e.target);
      try {
        await api("/api/purchases", { method: "POST", body: { date: d.date, product_id: Number(d.product_id),
          quantity: Number(d.quantity), unit_cost: d.unit_cost ? Number(d.unit_cost) : null, supplier: d.supplier, doc_number: d.doc_number } });
        closeModal(); toast("Marfa a fost adăugată în stoc."); setMonthFromDate(d.date); render();
      } catch (err) { toast(err.message, "err"); }
    });
  });
}

const STATUS_LABEL = { ok: "În stoc", low: "Sub minim", out: "Epuizat" };

async function renderStock(view) {
  const [inv, purchases] = await Promise.all([
    api(`/api/inventory?month=${state.month}`), api(`/api/purchases?month=${state.month}`), loadCatalog(),
  ]);
  const products = state.products;
  const value = products.reduce((s, p) => s + p.stock_value, 0);
  const alerts = products.filter((p) => p.status !== "ok" && p.active);
  const received = purchases.reduce((s, x) => s + x.value, 0);

  view.innerHTML = `
    <section class="stat-strip">
      <div class="stat"><span>Valoarea stocului azi</span><strong>${lei(value)}</strong></div>
      <div class="stat"><span>Produse</span><strong>${products.filter((p) => p.active).length}</strong></div>
      <div class="stat"><span>Sub stocul minim</span><strong style="color:${alerts.length ? "var(--gold)" : "var(--green)"}">${alerts.length}</strong></div>
      <div class="stat"><span>Marfă primită în ${esc(monthLabel(state.month))}</span><strong>${lei(received)}</strong></div>
    </section>

    <div class="card-head mt" style="margin-bottom:14px">
      <div class="segmented" id="stock-tabs">
        <button type="button" data-tab="products" class="${stockTab === "products" ? "active" : ""}">Produse</button>
        <button type="button" data-tab="nir" class="${stockTab === "nir" ? "active" : ""}">Recepții (NIR)</button>
        <button type="button" data-tab="inventory" class="${stockTab === "inventory" ? "active" : ""}">Fișă de inventar</button>
      </div>
      <div class="toolbar">
        <button class="btn" id="new-product" type="button">${icon("plus")}Produs nou</button>
        <button class="btn btn-primary" id="receive" type="button">${icon("truck")}Recepție marfă</button>
      </div>
    </div>

    <section class="card glass ${stockTab === "products" ? "" : "hidden"}" data-panel="products">
      <div class="card-head"><div><h2>Produse și stoc actual</h2><p>Stocul scade automat la fiecare vânzare și crește la recepții.</p></div>
        <div class="toolbar"><label class="field search">${icon("search")}<input id="prod-search" placeholder="Caută cod, produs, furnizor…"></label></div></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Cod</th><th>Produs</th><th>Stoc</th><th class="r">Preț</th><th class="r">Cost</th><th class="r">Marjă</th><th class="r">Valoare stoc</th><th>Se termină în</th><th></th></tr></thead>
        <tbody id="prod-rows">${products.map((p) => `
          <tr data-search="${esc(`${p.code} ${p.name} ${p.category} ${p.supplier}`.toLowerCase())}" class="${p.active ? "" : "inactive"}">
            <td class="mono">${esc(p.code)}</td>
            <td class="prod-cell"><b>${esc(p.name)}</b><br><small class="muted">${esc(p.category)} · ${esc(p.supplier || "—")}</small></td>
            <td style="min-width:150px"><div class="stock-cell"><span class="tag st-${p.status}">${STATUS_LABEL[p.status]}</span><b>${p.stock}</b><small class="muted">/ min ${p.min_stock}</small></div>
              <div class="bar"><i data-w="${Math.min(100, (p.stock / Math.max(p.min_stock * 3, 1)) * 100)}%" style="background:${p.status === "ok" ? "var(--green)" : p.status === "low" ? "var(--gold)" : "var(--red)"}"></i></div></td>
            <td class="r">${lei(p.sale_price, true)}</td>
            <td class="r">${lei(p.cost, true)}</td>
            <td class="r">${pct(p.margin_pct)}</td>
            <td class="r"><b>${lei(p.stock_value)}</b></td>
            <td>${p.days_left === null ? '<span class="muted">—</span>' : `<span class="${p.days_left <= 7 ? "neg" : p.days_left <= 14 ? "warn" : ""}">~${p.days_left} zile</span>`}</td>
            <td class="actions">
              <button class="icon-btn" data-receive="${p.id}" title="Recepție marfă">${icon("truck")}</button>
              <button class="icon-btn" data-edit-product="${p.id}" title="Editează">${icon("edit")}</button>
            </td>
          </tr>`).join("")}</tbody>
        <tfoot><tr><td colspan="6">Total stoc</td><td class="r">${lei(value)}</td><td colspan="2"></td></tr></tfoot>
      </table></div>
    </section>

    <section class="card glass ${stockTab === "nir" ? "" : "hidden"}" data-panel="nir">
      <div class="card-head"><div><h2>Recepții de marfă — ${esc(monthLabel(state.month))}</h2><p>${purchases.length} documente · ${lei(received, true)} fără TVA</p></div></div>
      ${purchases.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Data</th><th>NIR</th><th>Furnizor</th><th>Produs</th><th class="r">Cant.</th><th class="r">Cost / buc.</th><th class="r">Valoare</th><th>Plată</th><th></th></tr></thead>
        <tbody id="nir-rows">${purchases.map((x) => `
          <tr data-search="${esc(`${x.doc_number} ${x.supplier} ${x.product_name}`.toLowerCase())}">
            <td>${formatDate(x.date)}</td><td class="mono">${esc(x.doc_number)}</td><td>${esc(x.supplier)}</td>
            <td>${esc(x.product_code)} · ${esc(x.product_name)}</td><td class="r">${x.quantity}</td>
            <td class="r">${lei(x.unit_cost, true)}</td><td class="r"><b>${lei(x.value, true)}</b></td>
            <td>${x.paid ? `<span class="tag paid">${icon("check")}Plătit</span>` : `<span class="tag ${x.due_date < todayISO() ? "late" : "unpaid"}">Scadent ${formatDate(x.due_date).slice(0, 5)}</span>`}</td>
            <td class="actions"><button class="icon-btn danger" data-del-nir="${x.id}" title="Șterge">${icon("trash")}</button></td>
          </tr>`).join("")}</tbody>
      </table></div>` : emptyState("Nicio recepție de marfă în această lună.")}
    </section>

    <section class="card glass ${stockTab === "inventory" ? "" : "hidden"}" data-panel="inventory">
      <div class="card-head"><div><h2>Fișă de inventar — ${esc(monthLabel(state.month))}</h2><p>Stoc inițial + intrări − ieșiri = stoc final, la fel ca în raportul contabil.</p></div></div>
      <div class="table-wrap"><table class="compact">
        <thead><tr><th>Cod</th><th>Produs</th><th class="r">Inițial</th><th class="r">Intrări</th><th class="r">Ieșiri</th><th class="r">Final</th><th class="r">Cost</th><th class="r">Valoare</th><th>Control</th></tr></thead>
        <tbody>${inv.lines.map((l) => `<tr>
          <td class="mono">${esc(l.code)}</td><td>${esc(l.name)}</td><td class="r">${l.initial}</td>
          <td class="r" style="color:var(--green)">+${l.entries}</td><td class="r" style="color:var(--red)">−${l.exits}</td>
          <td class="r"><b>${l.final}</b></td><td class="r">${lei(l.cost)}</td><td class="r">${lei(l.value)}</td>
          <td>${l.initial + l.entries - l.exits === l.final ? `<span class="tag paid">${icon("check")}OK</span>` : '<span class="tag late">Diferență</span>'}</td></tr>`).join("")}</tbody>
        <tfoot><tr><td colspan="3">Total</td><td class="r">+${inv.totals.entries}</td><td class="r">−${inv.totals.exits}</td><td></td><td></td><td class="r">${lei(inv.totals.value)}</td><td></td></tr></tfoot>
      </table></div>
    </section>`;

  animateBars(view);
  paginate(view, "#prod-rows", "#prod-search", 50);
  $$("#stock-tabs button").forEach((b) => b.addEventListener("click", () => {
    stockTab = b.dataset.tab;
    $$("#stock-tabs button").forEach((x) => x.classList.toggle("active", x === b));
    $$("[data-panel]", view).forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== stockTab));
  }));
  $("#receive").addEventListener("click", () => openReceive(alerts[0]?.id));
  $("#new-product").addEventListener("click", () => {
    openModal("Produs nou", `<form id="product-form">${productFormHTML()}
      <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
      <button class="btn btn-primary" type="submit">${icon("check")}Adaugă produsul</button></div></form>`, (body) => {
      $("#product-form", body).addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await api("/api/products", { method: "POST", body: productPayload(e.target) }); closeModal(); toast("Produsul a fost adăugat."); render(); }
        catch (err) { toast(err.message, "err"); }
      });
    });
  });
  view.addEventListener("click", async (e) => {
    const receive = e.target.closest("[data-receive]"), edit = e.target.closest("[data-edit-product]"), delNir = e.target.closest("[data-del-nir]");
    if (receive) openReceive(Number(receive.dataset.receive));
    if (edit) {
      const p = products.find((x) => x.id === Number(edit.dataset.editProduct));
      openModal(`Editează ${p.name}`, `<form id="product-form">${productFormHTML(p)}
        <label class="check" style="margin-top:12px"><input type="checkbox" name="active" ${p.active ? "checked" : ""}><span>Produs activ (apare la vânzări)</span></label>
        <div class="form-actions"><button class="btn btn-danger" type="button" id="del-product">${icon("trash")}Șterge</button>
        <button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
        <button class="btn btn-primary" type="submit">${icon("check")}Salvează</button></div></form>`, (body) => {
        $("#product-form", body).addEventListener("submit", async (ev) => {
          ev.preventDefault();
          try {
            await api(`/api/products/${p.id}`, { method: "PUT", body: { ...productPayload(ev.target), active: $("[name=active]", ev.target).checked } });
            closeModal(); toast("Produsul a fost salvat."); render();
          } catch (err) { toast(err.message, "err"); }
        });
        $("#del-product", body).addEventListener("click", async () => {
          try { await api(`/api/products/${p.id}`, { method: "DELETE" }); closeModal(); toast("Produsul a fost șters."); render(); }
          catch (err) { toast(err.message, "err"); }
        });
      });
    }
    if (delNir && await confirmBox("Ștergeți recepția?", "Cantitatea va fi scăzută din stoc.")) {
      try { await api(`/api/purchases/${delNir.dataset.delNir}`, { method: "DELETE" }); toast("Recepția a fost ștearsă."); render(); }
      catch (err) { toast(err.message, "err"); }
    }
  });
}

/* ================= Clienți ================= */

function clientFormHTML(c = {}) {
  const types = ["B2B", "B2C", "Marketplace", "Online"];
  return `
    <div class="form-grid">
      <label class="field" style="grid-column:1/-1"><span>Nume client</span><input name="name" required maxlength="120" value="${esc(c.name || "")}" placeholder="ex. Alfa Office SRL"></label>
      <label class="field"><span>Tip</span><select name="type">${types.map((t) => `<option ${t === (c.type || "B2B") ? "selected" : ""}>${t}</option>`).join("")}</select></label>
      <label class="field"><span>Oraș</span><input name="city" maxlength="80" value="${esc(c.city || "")}"></label>
      <label class="field"><span>Agent responsabil</span><input name="agent" maxlength="80" value="${esc(c.agent || "")}"></label>
      <label class="field"><span>Termen de plată (zile)</span><input type="number" name="payment_terms" min="0" max="365" value="${esc(c.payment_terms ?? 0)}"><small>0 = plătește pe loc.</small></label>
    </div>`;
}

function clientPayload(form) {
  const d = formData(form);
  return { ...d, payment_terms: Number(d.payment_terms) || 0 };
}

async function renderClients(view) {
  const [clients, rec] = await Promise.all([api(`/api/clients?month=${state.month}`), api("/api/receivables")]);
  const activeMonth = clients.filter((c) => c.month_sales > 0).length;
  const today = todayISO();

  view.innerHTML = `
    <section class="stat-strip">
      <div class="stat"><span>De încasat (cu TVA)</span><strong>${lei(rec.total)}</strong></div>
      <div class="stat"><span>Trecut de scadență</span><strong style="color:${rec.overdue ? "var(--red)" : "var(--green)"}">${lei(rec.overdue)}</strong></div>
      <div class="stat"><span>Facturi neîncasate</span><strong>${rec.count}</strong></div>
      <div class="stat"><span>Clienți activi în ${esc(monthLabel(state.month))}</span><strong>${activeMonth} / ${clients.length}</strong></div>
    </section>

    <section class="grid cols-2 mt" style="align-items:start">
      <article class="card glass">
        <div class="card-head"><div><h2>Clienți</h2><p>Vânzări fără TVA în ${esc(monthLabel(state.month))} și în total</p></div>
          <button class="btn btn-primary" id="add-client" type="button">${icon("plus")}Client nou</button></div>
        <div class="table-wrap"><table class="compact">
          <thead><tr><th>Client</th><th>Termen</th><th class="r">Luna</th><th class="r">Total</th><th class="r">De încasat</th><th></th></tr></thead>
          <tbody>${clients.map((c) => `<tr>
            <td><b>${esc(c.name)}</b> <span class="tag">${esc(c.type)}</span><br><small class="muted">${esc([c.city, c.agent].filter(Boolean).join(" · ") || "—")}</small></td>
            <td>${c.payment_terms ? `${c.payment_terms} zile` : "pe loc"}</td>
            <td class="r">${lei(c.month_sales)}</td>
            <td class="r">${lei(c.total_sales)}</td>
            <td class="r">${c.receivable ? `<b style="color:${c.overdue ? "var(--red)" : "var(--gold)"}">${lei(c.receivable)}</b>` : '<span class="muted">—</span>'}</td>
            <td class="actions"><button class="icon-btn" data-edit-client="${c.id}" title="Editează">${icon("edit")}</button></td>
          </tr>`).join("")}</tbody>
        </table></div>
      </article>

      <article class="card glass">
        <div class="card-head"><div><h2>Facturi de încasat</h2><p>Cele mai vechi scadențe primele</p></div></div>
        ${rec.invoices.length ? `<ul class="due-list" id="due-list">${rec.invoices.map((i) => {
          const late = i.due_date < today;
          return `<li class="${late ? "late" : ""}" data-search="${esc(`${i.invoice_number} ${i.client_name}`.toLowerCase())}">
            <div><b>${esc(i.client_name || "—")}</b><small>${esc(i.invoice_number || "")} · scadent ${formatDate(i.due_date)}${late ? " · restantă" : ""}</small></div>
            <strong>${lei(i.amount, true)}</strong>
            <button class="btn btn-sm" data-collect="${i.id}" type="button">${icon("check")}Încasat</button>
          </li>`;
        }).join("")}</ul>` : emptyState("Toate facturile sunt încasate.")}
      </article>
    </section>`;

  const openForm = (c) => openModal(c ? `Editează ${c.name}` : "Client nou", `<form id="client-form">${clientFormHTML(c)}
    <div class="form-actions">${c ? `<button class="btn btn-danger" type="button" id="del-client">${icon("trash")}Șterge</button>` : ""}
    <button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
    <button class="btn btn-primary" type="submit">${icon("check")}Salvează</button></div></form>`, (body) => {
    $("#client-form", body).addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api(c ? `/api/clients/${c.id}` : "/api/clients", { method: c ? "PUT" : "POST", body: clientPayload(e.target) });
        closeModal(); toast("Clientul a fost salvat."); render();
      } catch (err) { toast(err.message, "err"); }
    });
    $("#del-client", body)?.addEventListener("click", async () => {
      try { await api(`/api/clients/${c.id}`, { method: "DELETE" }); closeModal(); toast("Clientul a fost șters."); render(); }
      catch (err) { toast(err.message, "err"); }
    });
  });
  $("#add-client").addEventListener("click", () => openForm());
  view.addEventListener("click", async (e) => {
    const edit = e.target.closest("[data-edit-client]"), collect = e.target.closest("[data-collect]");
    if (edit) openForm(clients.find((c) => c.id === Number(edit.dataset.editClient)));
    if (collect) {
      try {
        await api(`/api/sales/${collect.dataset.collect}/paid`, { method: "PATCH", body: { paid: true } });
        toast("Factura a fost marcată încasată."); render();
      } catch (err) { toast(err.message, "err"); }
    }
  });
}

/* ================= Furnizori ================= */

function supplierFormHTML(s = {}) {
  return `
    <div class="form-grid">
      <label class="field" style="grid-column:1/-1"><span>Nume furnizor</span><input name="name" required maxlength="120" value="${esc(s.name || "")}"></label>
      <label class="field"><span>Termen de plată (zile)</span><input type="number" name="payment_terms" min="0" max="365" value="${esc(s.payment_terms ?? 30)}"><small>De obicei 15–30 de zile.</small></label>
      <label class="field"><span>Contact (opțional)</span><input name="contact" maxlength="200" value="${esc(s.contact || "")}" placeholder="telefon, email"></label>
    </div>`;
}

async function renderSuppliers(view) {
  const [suppliers, pay] = await Promise.all([api(`/api/suppliers?month=${state.month}`), api("/api/payables")]);
  const monthTotal = suppliers.reduce((s, x) => s + x.month_purchases, 0);
  const today = todayISO();

  view.innerHTML = `
    <section class="stat-strip">
      <div class="stat"><span>De plătit furnizorilor (cu TVA)</span><strong>${lei(pay.total)}</strong></div>
      <div class="stat"><span>Scadent în următoarele ${pay.soon_days} zile</span><strong style="color:${pay.due_soon ? "var(--gold)" : "inherit"}">${lei(pay.due_soon)}</strong></div>
      <div class="stat"><span>Trecut de scadență</span><strong style="color:${pay.overdue ? "var(--red)" : "var(--green)"}">${lei(pay.overdue)}</strong></div>
      <div class="stat"><span>Marfă cumpărată în ${esc(monthLabel(state.month))}</span><strong>${lei(monthTotal)}</strong></div>
    </section>

    <section class="grid cols-2 mt" style="align-items:start">
      <article class="card glass">
        <div class="card-head"><div><h2>Furnizori</h2><p>Termenul de plată se aplică automat la fiecare recepție de marfă.</p></div>
          <button class="btn btn-primary" id="add-supplier" type="button">${icon("plus")}Furnizor nou</button></div>
        <div class="table-wrap"><table class="compact">
          <thead><tr><th>Furnizor</th><th>Termen</th><th class="r">Luna</th><th class="r">Total cumpărat</th><th class="r">De plătit</th><th></th></tr></thead>
          <tbody>${suppliers.map((s) => `<tr>
            <td><b>${esc(s.name)}</b><br><small class="muted">${s.products} produse${s.contact ? ` · ${esc(s.contact)}` : ""}</small></td>
            <td>${s.payment_terms ? `${s.payment_terms} zile` : "pe loc"}</td>
            <td class="r">${lei(s.month_purchases)}</td>
            <td class="r">${lei(s.total_purchases)}</td>
            <td class="r">${s.payable ? `<b style="color:${s.overdue ? "var(--red)" : "var(--gold)"}">${lei(s.payable)}</b>` : '<span class="muted">—</span>'}</td>
            <td class="actions"><button class="icon-btn" data-edit-supplier="${s.id}" title="Editează">${icon("edit")}</button></td>
          </tr>`).join("")}</tbody>
        </table></div>
      </article>

      <article class="card glass">
        <div class="card-head"><div><h2>Plăți de făcut</h2><p>În ordinea scadenței</p></div></div>
        ${pay.documents.length ? `<ul class="due-list">${pay.documents.map((d) => `
          <li class="${d.overdue ? "late" : d.due_soon ? "" : "later"}">
            <div><b>${esc(d.supplier)}</b><small>${esc(d.doc_number)} · ${esc(d.product)} · scadent ${formatDate(d.due_date)}${d.overdue ? " · restant" : d.due_soon ? " · săptămâna asta" : ""}</small></div>
            <strong>${lei(d.amount, true)}</strong>
            <button class="btn btn-sm" data-pay="${d.id}" type="button">${icon("check")}Plătit</button>
          </li>`).join("")}</ul>` : emptyState("Nu aveți nimic de plătit furnizorilor.")}
      </article>
    </section>`;

  const openForm = (s) => openModal(s ? `Editează ${s.name}` : "Furnizor nou", `<form id="supplier-form">${supplierFormHTML(s)}
    <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
    <button class="btn btn-primary" type="submit">${icon("check")}Salvează</button></div></form>`, (body) => {
    $("#supplier-form", body).addEventListener("submit", async (e) => {
      e.preventDefault();
      const d = formData(e.target);
      try {
        await api(s ? `/api/suppliers/${s.id}` : "/api/suppliers", { method: s ? "PUT" : "POST",
          body: { ...d, payment_terms: Number(d.payment_terms) || 0 } });
        closeModal(); toast("Furnizorul a fost salvat."); render();
      } catch (err) { toast(err.message, "err"); }
    });
  });
  $("#add-supplier").addEventListener("click", () => openForm());
  view.addEventListener("click", async (e) => {
    const edit = e.target.closest("[data-edit-supplier]"), payBtn = e.target.closest("[data-pay]");
    if (edit) openForm(suppliers.find((s) => s.id === Number(edit.dataset.editSupplier)));
    if (payBtn) {
      try {
        await api(`/api/purchases/${payBtn.dataset.pay}/paid`, { method: "PATCH", body: { paid: true } });
        toast("Plata a fost înregistrată."); render();
      } catch (err) { toast(err.message, "err"); }
    }
  });
}

/* ================= Cheltuieli ================= */

async function loadCategories() {
  state.categories = await api("/api/categories");
  return state.categories;
}
const categoryColor = (name) => state.categories.find((c) => c.name === name)?.color || "#94a3b8";

function expenseFormHTML(exp = {}) {
  return `
    <div class="form-grid">
      <label class="field"><span>Data</span><input type="date" name="date" required value="${esc(exp.date || defaultDate())}"></label>
      <label class="field"><span>Categorie</span><select name="category" required>
        ${state.categories.map((c) => `<option ${c.name === exp.category ? "selected" : ""}>${esc(c.name)}</option>`).join("")}
      </select></label>
      <label class="field" style="grid-column:span 2"><span>Descriere</span><input name="description" maxlength="200" placeholder="ex. Factură energie electrică" value="${esc(exp.description || "")}"></label>
      <label class="field"><span>Furnizor</span><input name="supplier" maxlength="120" value="${esc(exp.supplier || "")}"></label>
      <label class="field"><span>Sumă fără TVA (lei)</span><input type="number" name="amount" min="0.01" step="0.01" required placeholder="0,00" value="${esc(exp.amount ?? "")}"></label>
      <label class="field"><span>Cotă TVA</span><select name="vat_kind">
        ${Object.entries(VAT_KINDS).map(([k, label]) => `<option value="${k}" ${k === (exp.vat_kind || categoryVat(exp.category || state.categories[0]?.name)) ? "selected" : ""}>${label}</option>`).join("")}
      </select></label>
    </div>
    <p class="muted" style="font-size:12px;margin:8px 0 0">Marfa pentru vânzare se introduce la <a href="#stoc" onclick="closeModal()">Stoc → Recepție marfă</a>, nu aici.</p>`;
}

const VAT_KINDS = { standard: "Standard (21%)", reduced: "Redusă (11%)", none: "Fără TVA (scutit)" };
const categoryVat = (name) => state.categories.find((c) => c.name === name)?.vat_kind || "standard";

// Cota de TVA se schimbă automat după categorie (de exemplu comisioanele bancare sunt scutite).
function wireExpenseForm(form) {
  const category = $("[name=category]", form), vat = $("[name=vat_kind]", form);
  category?.addEventListener("change", () => { vat.value = categoryVat(category.value); });
}

function expensePayload(form) {
  const d = formData(form);
  return { date: d.date, category: d.category, description: d.description, amount: Number(d.amount),
    supplier: d.supplier, vat_kind: d.vat_kind };
}

async function renderExpenses(view) {
  const [expenses, summary] = await Promise.all([
    api(`/api/expenses?month=${state.month}`), api(`/api/summary?month=${state.month}`), loadCategories(),
  ]);
  const total = expenses.reduce((s, x) => s + x.amount, 0);
  const cats = Object.entries(summary.expenses_by_category);
  const maxCat = Math.max(...cats.map((c) => c[1]), 1);

  view.innerHTML = `
    <section class="grid cols-2" style="align-items:start">
      <article class="card glass">
        <div class="card-head"><div><h2>Adaugă o cheltuială</h2><p>Facturi, chirie, utilități, transport…</p></div>
          <button class="btn btn-sm" id="manage-cats" type="button">${icon("settings")}Categorii</button></div>
        <form id="expense-form">${expenseFormHTML()}
          <div class="form-actions"><button class="btn btn-primary" type="submit">${icon("plus")}Adaugă cheltuiala</button></div>
        </form>
      </article>
      <article class="card glass">
        <div class="card-head"><div><h2>Pe categorii</h2><p>Total: <b style="color:var(--text)">${lei(total)}</b> · fără salarii și taxe</p></div></div>
        ${cats.length ? `<div class="bars">${cats.map(([name, value]) => `
          <div class="bar-row"><header><span>${esc(name)}</span><span>${lei(value)} · ${pct((value / total) * 100)}</span></header>
          <div class="bar"><i data-w="${(value / maxCat) * 100}%" style="background:${esc(categoryColor(name))}"></i></div></div>`).join("")}</div>`
          : emptyState("Nicio cheltuială în această lună.")}
      </article>
    </section>

    <section class="card glass mt">
      <div class="card-head">
        <div><h2>Cheltuieli — ${esc(monthLabel(state.month))}</h2><p>${expenses.length} înregistrări</p></div>
        <div class="toolbar"><label class="field search">${icon("search")}<input id="exp-search" placeholder="Caută…"></label></div>
      </div>
      ${expenses.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Data</th><th>Categorie</th><th>Descriere</th><th>Furnizor</th><th class="r">Sumă</th><th></th></tr></thead>
        <tbody id="exp-rows">${expenses.map((x) => `
          <tr data-search="${esc(`${x.category} ${x.description} ${x.supplier || ""}`.toLowerCase())}">
            <td>${formatDate(x.date)}</td>
            <td><span class="tag"><span class="sw" style="background:${esc(categoryColor(x.category))}"></span>${esc(x.category)}</span></td>
            <td>${esc(x.description) || '<span class="muted">—</span>'}${x.vat_kind !== "standard" ? ` <span class="tag">${x.vat_kind === "none" ? "fără TVA" : "TVA 11%"}</span>` : ""}</td>
            <td>${esc(x.supplier || "—")}</td>
            <td class="r"><b>${lei(x.amount, true)}</b></td>
            <td class="actions">
              <button class="icon-btn" data-edit="${x.id}" title="Editează">${icon("edit")}</button>
              <button class="icon-btn danger" data-del="${x.id}" title="Șterge">${icon("trash")}</button>
            </td>
          </tr>`).join("")}</tbody>
        <tfoot><tr><td colspan="4">Total lună</td><td class="r">${lei(total, true)}</td><td></td></tr></tfoot>
      </table></div>` : emptyState("Nu există cheltuieli în această lună.")}
    </section>`;

  animateBars(view);
  $("#manage-cats").addEventListener("click", () => openCategories(render));
  wireExpenseForm($("#expense-form"));
  $("#expense-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const payload = expensePayload(e.target);
      await api("/api/expenses", { method: "POST", body: payload });
      toast(`Cheltuială adăugată: ${lei(payload.amount, true)}`);
      setMonthFromDate(payload.date);
      render();
    } catch (err) { toast(err.message, "err"); }
  });
  paginate(view, "#exp-rows", "#exp-search");
  view.addEventListener("click", async (e) => {
    const edit = e.target.closest("[data-edit]"), del = e.target.closest("[data-del]");
    if (edit) {
      const exp = expenses.find((x) => x.id === Number(edit.dataset.edit));
      openModal("Editează cheltuiala", `<form id="edit-exp">${expenseFormHTML(exp)}
        <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
        <button class="btn btn-primary" type="submit">${icon("check")}Salvează</button></div></form>`, (body) => {
        wireExpenseForm($("#edit-exp", body));
        $("#edit-exp", body).addEventListener("submit", async (ev) => {
          ev.preventDefault();
          try {
            const payload = expensePayload(ev.target);
            await api(`/api/expenses/${exp.id}`, { method: "PUT", body: payload });
            closeModal(); toast("Cheltuiala a fost actualizată."); setMonthFromDate(payload.date); render();
          } catch (err) { toast(err.message, "err"); }
        });
      });
    }
    if (del && await confirmBox("Ștergeți cheltuiala?", "Cheltuiala va fi ștearsă definitiv.")) {
      try { await api(`/api/expenses/${del.dataset.del}`, { method: "DELETE" }); toast("Cheltuiala a fost ștearsă."); render(); }
      catch (err) { toast(err.message, "err"); }
    }
  });
}

function categoriesHTML() {
  return `
    <ul class="legend" style="gap:6px;margin-bottom:16px">
      ${state.categories.map((c) => `<li style="grid-template-columns:12px 1fr auto"><span class="sw" style="background:${esc(c.color)}"></span><span>${esc(c.name)}</span>
        <button class="icon-btn danger" data-delcat="${c.id}" title="Șterge">${icon("trash")}</button></li>`).join("")}
    </ul>
    <form id="cat-form" class="form-grid" style="grid-template-columns:1fr 70px auto;align-items:end">
      <label class="field"><span>Categorie nouă</span><input name="name" required maxlength="100" placeholder="ex. Asigurări"></label>
      <label class="field"><span>Culoare</span><input type="color" name="color" value="#22d3ee" style="padding:4px;height:46px"></label>
      <button class="btn btn-primary" type="submit">${icon("plus")}Adaugă</button>
    </form>`;
}

function openCategories(onChange) {
  const mount = (body) => {
    $("#cat-form", body).addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api("/api/categories", { method: "POST", body: formData(e.target) });
        await loadCategories(); body.innerHTML = categoriesHTML(); mount(body); toast("Categorie adăugată."); onChange?.();
      } catch (err) { toast(err.message, "err"); }
    });
    $$("[data-delcat]", body).forEach((b) => b.addEventListener("click", async () => {
      try {
        await api(`/api/categories/${b.dataset.delcat}`, { method: "DELETE" });
        await loadCategories(); body.innerHTML = categoriesHTML(); mount(body); toast("Categorie ștearsă."); onChange?.();
      } catch (err) { toast(err.message, "err"); }
    }));
  };
  loadCategories().then(() => openModal("Categorii de cheltuieli", categoriesHTML(), mount));
}

/* ================= Angajați ================= */

function previewHTML(p, current) {
  const diff = current ? p.net - current.net : null;
  return `
    <div class="row"><span>Salariu brut</span><b>${lei(p.gross, true)}</b></div>
    <div class="row"><span>− CAS (pensie)</span><b>${lei(p.cas, true)}</b></div>
    <div class="row"><span>− CASS (sănătate)</span><b>${lei(p.cass, true)}</b></div>
    <div class="row"><span>− Impozit pe venit</span><b>${lei(p.income_tax, true)}</b></div>
    <div class="row big"><span>Salariu net (primește angajatul)</span><b>${lei(p.net, true)}</b></div>
    <div class="row"><span>+ CAM plătit de firmă</span><b>${lei(p.cam, true)}</b></div>
    <div class="row big"><span>Cost total pentru firmă</span><b style="color:var(--gold)">${lei(p.employer_cost, true)}</b></div>
    ${diff !== null ? `<div class="row"><span>Diferență net față de acum</span><b style="color:${diff >= 0 ? "var(--green)" : "var(--red)"}">${diff >= 0 ? "+" : ""}${lei(diff, true)}</b></div>` : ""}`;
}

function wirePreview(body, current) {
  const input = $("[name=gross]", body), out = $(".preview", body);
  let timer;
  const update = () => {
    clearTimeout(timer);
    const gross = Number(input.value);
    if (!(gross > 0)) { out.classList.add("hidden"); return; }
    timer = setTimeout(async () => {
      try {
        const p = await api(`/api/salary-preview?gross=${gross}`);
        out.innerHTML = previewHTML(p, current);
        out.classList.remove("hidden");
      } catch { /* valoare invalidă în timpul tastării */ }
    }, 180);
  };
  input.addEventListener("input", update);
  update();
}

async function renderEmployees(view) {
  const [employees, pay] = await Promise.all([api("/api/employees"), api(`/api/payroll?month=${state.month}`)]);
  const t = pay.totals;
  const active = employees.filter((e) => e.active);

  view.innerHTML = `
    <section class="stat-strip">
      <div class="stat"><span>Angajați activi</span><strong>${active.length}</strong></div>
      <div class="stat"><span>Total brut — ${esc(monthLabel(state.month))}</span><strong>${lei(t.gross)}</strong></div>
      <div class="stat"><span>Total net plătit</span><strong>${lei(t.net)}</strong></div>
      <div class="stat"><span>Cost total firmă</span><strong style="color:var(--gold)">${lei(t.employer_cost)}</strong></div>
    </section>
    ${pay.warnings.length ? `<ul class="insights mt">${pay.warnings.map((w) => `<li class="insight bad"><span class="ic">${icon("alert")}</span><span>${esc(w)}</span></li>`).join("")}</ul>` : ""}

    <div class="card-head mt" style="margin-bottom:14px">
      <div><h2>Echipa</h2><p>Adăugați angajați și modificați salariile pe măsură ce evoluează.</p></div>
      <button class="btn btn-primary" id="add-emp" type="button">${icon("plus")}Adaugă angajat</button>
    </div>

    ${employees.length ? `<section class="employees">${employees.map((e) => `
      <article class="card glass emp ${e.active ? "" : "inactive"}">
        <div class="emp-head">
          <div class="avatar" style="background:${gradientFor(e.name)}">${esc(initials(e.name))}</div>
          <div style="flex:1;min-width:0"><h3>${esc(e.name)}</h3><p>${esc(e.role || "—")}</p></div>
          ${e.active ? "" : '<span class="tag">Inactiv</span>'}
          ${e.hours_per_day < 8 ? `<span class="tag">${e.hours_per_day} ore/zi</span>` : ""}
        </div>
        ${e.below_min_wage && e.active ? `<p class="emp-warn">${icon("alert")}Sub salariul minim (${lei(e.min_wage)} pentru norma lui)</p>` : ""}
        <div class="emp-pay">
          <div><span>Brut</span><strong>${lei(e.salary.gross)}</strong></div>
          <div><span>Net</span><strong style="color:var(--cyan)">${lei(e.salary.net)}</strong></div>
          <div><span>Cost firmă</span><strong style="color:var(--gold)">${lei(e.salary.employer_cost)}</strong></div>
        </div>
        <ul class="timeline">${e.history.map((h) => `<li><b>${lei(h.gross)}</b> brut din ${formatDate(h.effective_from)} · ${esc(h.note)}</li>`).join("")}
          <li>Angajat din <b>${formatDate(e.hire_date)}</b>${e.end_date ? ` · plecat ${formatDate(e.end_date)}` : ""}</li>
          <li>Concediu de odihnă ${currentMonth().slice(0, 4)}: <b>${e.leave_taken}</b> din ${e.leave_days} zile luate · <b style="color:${e.leave_left < 0 ? "var(--red)" : "var(--green)"}">${e.leave_left} rămase</b></li></ul>
        <div class="emp-actions">
          <button class="btn btn-sm btn-gold" data-raise="${e.id}" type="button">${icon("raise")}Modifică salariul</button>
          <button class="btn btn-sm" data-leave="${e.id}" type="button">${icon("calendar")}Concedii</button>
          <button class="icon-btn" data-edit="${e.id}" title="Editează">${icon("edit")}</button>
          <button class="icon-btn danger" data-del="${e.id}" title="Șterge">${icon("trash")}</button>
        </div>
      </article>`).join("")}</section>` : `<div class="card glass">${emptyState("Nu aveți încă angajați. Adăugați primul angajat.")}</div>`}

    <section class="card glass mt">
      <div class="card-head"><div><h2>Stat de plată — ${esc(monthLabel(state.month))}</h2><p>Calculat automat din salariile brute · ${pay.working_days} zile lucrătoare${pay.min_wage ? ` · salariul minim ${lei(pay.min_wage)}` : ""}. Concediul fără plată scade brutul proporțional; deducerea personală și indemnizația de concediu medical le aplică contabilul.</p></div></div>
      ${pay.lines.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Angajat</th><th class="r">Zile</th><th class="r">Brut</th><th class="r">CAS</th><th class="r">CASS</th><th class="r">Impozit</th><th class="r">Net</th><th class="r">CAM</th><th class="r">Cost firmă</th></tr></thead>
        <tbody>${pay.lines.map((l) => `<tr><td>${esc(l.name)}<br><small class="muted">${esc(l.role)}</small></td>
          <td class="r" title="${esc(absenceText(l.absences))}">${l.worked_days}/${l.working_days}${l.worked_days < l.working_days ? "<br><small class=\"muted\">" + esc(absenceText(l.absences)) + "</small>" : ""}</td>
          <td class="r">${lei(l.gross, true)}${l.gross !== l.base_gross ? `<br><small class="muted">din ${lei(l.base_gross)}</small>` : ""}</td><td class="r">${lei(l.cas, true)}</td><td class="r">${lei(l.cass, true)}</td>
          <td class="r">${lei(l.income_tax, true)}</td><td class="r"><b style="color:var(--cyan)">${lei(l.net, true)}</b></td>
          <td class="r">${lei(l.cam, true)}</td><td class="r"><b>${lei(l.employer_cost, true)}</b></td></tr>`).join("")}</tbody>
        <tfoot><tr><td>Total</td><td></td><td class="r">${lei(t.gross, true)}</td><td class="r">${lei(t.cas, true)}</td><td class="r">${lei(t.cass, true)}</td>
          <td class="r">${lei(t.income_tax, true)}</td><td class="r">${lei(t.net, true)}</td><td class="r">${lei(t.cam, true)}</td><td class="r">${lei(t.employer_cost, true)}</td></tr></tfoot>
      </table></div>` : emptyState("Niciun angajat activ în această lună.")}
    </section>`;

  $("#add-emp").addEventListener("click", () => {
    openModal("Angajat nou", `<form id="emp-form">
      <div class="form-grid">
        <label class="field" style="grid-column:1/-1"><span>Nume complet</span><input name="name" required maxlength="120" placeholder="ex. Maria Ionescu"></label>
        <label class="field"><span>Funcție</span><input name="role" maxlength="120" placeholder="ex. Vânzări"></label>
        <label class="field"><span>Data angajării</span><input type="date" name="hire_date" required value="${todayISO()}"></label>
        <label class="field" style="grid-column:1/-1"><span>Salariu brut (lei)</span><input type="number" name="gross" min="1" step="1" required placeholder="ex. 5000"></label>
        ${normFields({})}
      </div>
      <div class="preview hidden"></div>
      <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
      <button class="btn btn-primary" type="submit">${icon("check")}Adaugă angajatul</button></div></form>`, (body) => {
      wirePreview(body);
      $("#emp-form", body).addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const d = formData(ev.target);
        try {
          await api("/api/employees", { method: "POST", body: { ...d, gross: Number(d.gross), hours_per_day: Number(d.hours_per_day), leave_days: Number(d.leave_days) } });
          closeModal(); toast(`${d.name} a fost adăugat(ă) în echipă.`); render();
        } catch (err) { toast(err.message, "err"); }
      });
    });
  });

  view.addEventListener("click", async (ev) => {
    const raise = ev.target.closest("[data-raise]"), edit = ev.target.closest("[data-edit]"), del = ev.target.closest("[data-del]");
    const find = (el, attr) => employees.find((x) => x.id === Number(el.dataset[attr]));
    const leave = ev.target.closest("[data-leave]");
    if (leave) openAbsences(find(leave, "leave"));
    if (raise) {
      const e = find(raise, "raise");
      const nextMonth = `${shiftMonth(currentMonth(), 1)}-01`;
      openModal(`Salariu nou — ${e.name}`, `<form id="raise-form">
        <p class="muted" style="margin-top:0">Salariul actual: <b style="color:var(--text)">${lei(e.salary.gross)} brut</b> (${lei(e.salary.net)} net). Istoricul se păstrează.</p>
        <div class="form-grid">
          <label class="field"><span>Salariu brut nou (lei)</span><input type="number" name="gross" min="1" step="1" required value="${e.salary.gross}"></label>
          <label class="field"><span>Valabil de la</span><input type="date" name="effective_from" required value="${nextMonth}"></label>
          <label class="field" style="grid-column:1/-1"><span>Motiv (opțional)</span><input name="note" maxlength="200" placeholder="ex. Performanță foarte bună"></label>
        </div>
        <div class="preview hidden"></div>
        <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
        <button class="btn btn-gold" type="submit">${icon("check")}Salvează salariul</button></div></form>`, (body) => {
        wirePreview(body, e.salary);
        $("#raise-form", body).addEventListener("submit", async (sub) => {
          sub.preventDefault();
          const d = formData(sub.target);
          try {
            await api(`/api/employees/${e.id}/salary`, { method: "POST", body: { ...d, gross: Number(d.gross) } });
            closeModal(); toast(`Salariul lui ${e.name} a fost actualizat.`); render();
          } catch (err) { toast(err.message, "err"); }
        });
      });
    }
    if (edit) {
      const e = find(edit, "edit");
      openModal(`Editează — ${e.name}`, `<form id="edit-emp">
        <div class="form-grid">
          <label class="field" style="grid-column:1/-1"><span>Nume complet</span><input name="name" required maxlength="120" value="${esc(e.name)}"></label>
          <label class="field" style="grid-column:1/-1"><span>Funcție</span><input name="role" maxlength="120" value="${esc(e.role)}"></label>
          <label class="field"><span>Data angajării</span><input type="date" name="hire_date" required value="${esc(e.hire_date)}"></label>
          <label class="field"><span>Data plecării</span><input type="date" name="end_date" value="${esc(e.end_date || "")}"><small>Lăsați gol dacă lucrează în continuare.</small></label>
          ${normFields(e)}
          <label class="field" style="grid-column:1/-1"><span>Notițe</span><textarea name="notes" rows="2" maxlength="500">${esc(e.notes)}</textarea></label>
        </div>
        <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
        <button class="btn btn-primary" type="submit">${icon("check")}Salvează</button></div></form>`, (body) => {
        $("#edit-emp", body).addEventListener("submit", async (sub) => {
          sub.preventDefault();
          const d = formData(sub.target);
          try {
            await api(`/api/employees/${e.id}`, { method: "PUT", body: { ...d, end_date: d.end_date || null, hours_per_day: Number(d.hours_per_day), leave_days: Number(d.leave_days) } });
            closeModal(); toast("Datele angajatului au fost salvate."); render();
          } catch (err) { toast(err.message, "err"); }
        });
      });
    }
    if (del) {
      const e = find(del, "del");
      if (await confirmBox(`Ștergeți pe ${e.name}?`, "Se șterge și tot istoricul salarial, inclusiv din lunile trecute. Dacă angajatul a plecat, mai bine completați „Data plecării” la Editează.")) {
        try { await api(`/api/employees/${e.id}`, { method: "DELETE" }); toast("Angajatul a fost șters."); render(); }
        catch (err) { toast(err.message, "err"); }
      }
    }
  });
}

const ABSENCE_LABELS = { odihna: "Concediu de odihnă", medical: "Concediu medical", fara_plata: "Concediu fără plată" };
const absenceText = (a) => Object.entries(a || {}).filter(([, v]) => v).map(([k, v]) => `${ABSENCE_LABELS[k]}: ${v} zile`).join(", ");

function normFields(e) {
  return `
    <label class="field"><span>Normă</span><select name="hours_per_day">${[8, 6, 4, 2].map((h) =>
      `<option value="${h}" ${(e.hours_per_day || 8) === h ? "selected" : ""}>${h === 8 ? "Normă întreagă (8 ore)" : `${h} ore pe zi`}</option>`).join("")}</select></label>
    <label class="field"><span>Zile de concediu pe an</span><input type="number" name="leave_days" min="0" max="60" step="1" value="${e.leave_days ?? 21}"><small>Minimum legal: 20 de zile lucrătoare.</small></label>`;
}

function openAbsences(e) {
  openModal(`Concedii — ${esc(e.name)}`, `
    <p class="muted" style="margin-top:0">Concediul de odihnă și cel medical nu schimbă calculul aici (indemnizația medicală o calculează contabilul). Concediul fără plată scade salariul brut proporțional cu zilele lipsă.</p>
    <form id="absence-form"><div class="form-grid">
      <label class="field"><span>Luna</span><input type="month" name="month" required value="${state.month}"></label>
      <label class="field"><span>Tip</span><select name="kind">${Object.entries(ABSENCE_LABELS).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></label>
      <label class="field"><span>Zile lucrătoare</span><input type="number" name="days" min="1" max="23" step="1" required value="1"></label>
      <label class="field"><span>Notă</span><input name="note" maxlength="200" placeholder="opțional"></label>
    </div>
    <div class="form-actions"><button class="btn btn-primary" type="submit">${icon("plus")}Adaugă</button></div></form>
    <h3 style="margin:18px 0 8px;font-size:15px">Istoric</h3>
    ${e.absences.length ? `<ul class="timeline">${e.absences.map((a) => `<li style="display:flex;justify-content:space-between;gap:8px"><span><b>${monthLabel(a.month)}</b> · ${ABSENCE_LABELS[a.kind]}: ${a.days} zile${a.note ? ` · ${esc(a.note)}` : ""}</span>
      <button class="icon-btn danger" data-del-absence="${a.id}" title="Șterge">${icon("trash")}</button></li>`).join("")}</ul>` : '<p class="muted">Nicio absență înregistrată.</p>'}`, (body) => {
    $("#absence-form", body).addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const d = formData(ev.target);
      try {
        await api(`/api/employees/${e.id}/absences`, { method: "POST", body: { ...d, days: Number(d.days) } });
        closeModal(); toast("Absența a fost înregistrată."); render();
      } catch (err) { toast(err.message, "err"); }
    });
    body.addEventListener("click", async (ev) => {
      const del = ev.target.closest("[data-del-absence]");
      if (!del) return;
      try { await api(`/api/absences/${del.dataset.delAbsence}`, { method: "DELETE" }); closeModal(); toast("Absența a fost ștearsă."); render(); }
      catch (err) { toast(err.message, "err"); }
    });
  });
}

/* ================= Taxe ================= */

const rateTxt = (v) => String(Number(v)).replace(".", ",");

async function renderTaxes(view) {
  const [d, sample] = await Promise.all([
    api(`/api/dashboard?month=${state.month}`), api("/api/salary-preview?gross=100"),
  ]);
  // Cotele valabile în luna afișată, din regulile fiscale.
  const settings = { ...d.current.rates, tax_regime: d.current.tax_regime };
  const t = d.current.taxes;
  const salaryTaxes = t.total - t.company_tax;
  const share = d.current.revenue ? (t.total / d.current.revenue) * 100 : 0;
  const yearTaxes = d.trend.filter((m) => m.month.slice(0, 4) === state.month.slice(0, 4)).reduce((s, m) => s + m.taxes, 0);

  const explain = [
    ["CAS", "#a78bfa", "Contribuția la pensie", `${rateTxt(settings.cas_rate)}% din salariul brut, reținut din salariul angajatului.`, t.cas],
    ["CASS", "#34d399", "Contribuția la sănătate", `${rateTxt(settings.cass_rate)}% din salariul brut, reținut din salariul angajatului.`, t.cass],
    ["IV", "#22d3ee", "Impozit pe venit", `${rateTxt(settings.income_tax_rate)}% din ce rămâne după CAS și CASS.`, t.income_tax],
    ["CAM", "#fb923c", "Contribuția asiguratorie pentru muncă", `${rateTxt(settings.cam_rate)}% din brut, plătit de firmă peste salariu.`, t.cam],
    settings.tax_regime === "micro"
      ? ["μ", "#fbbf24", "Impozit microîntreprindere", `${rateTxt(settings.micro_tax_rate)}% din veniturile lunii (${lei(d.current.revenue)}).`, t.company_tax]
      : ["IP", "#fbbf24", "Impozit pe profit", `${rateTxt(settings.profit_tax_rate)}% din profitul lunii înainte de impozit (${lei(d.current.profit_before_tax)}). Dacă luna e pe pierdere, nu se plătește.`, t.company_tax],
  ];

  view.innerHTML = `
    <section class="grid kpis">
      <article class="card glass kpi" style="--accent:#f87171"><div class="kpi-top"><span class="kpi-label"><span class="kpi-icon">${icon("taxes")}</span>Total taxe — luna</span></div>
        <div class="kpi-value" data-count="${t.total}"></div><div class="kpi-foot"><span class="sub">${esc(monthLabel(state.month))}</span></div></article>
      <article class="card glass kpi" style="--accent:#a78bfa"><div class="kpi-top"><span class="kpi-label"><span class="kpi-icon">${icon("team")}</span>Din salarii</span></div>
        <div class="kpi-value" data-count="${salaryTaxes}"></div><div class="kpi-foot"><span class="sub">CAS + CASS + impozit + CAM</span></div></article>
      <article class="card glass kpi" style="--accent:#fbbf24"><div class="kpi-top"><span class="kpi-label"><span class="kpi-icon">${icon("percent")}</span>Din fiecare 100 lei încasați</span></div>
        <div class="kpi-value" data-count="${share}" data-suffix=" lei"></div><div class="kpi-foot"><span class="sub">merg la stat ca taxe</span></div></article>
      <article class="card glass kpi" style="--accent:#22d3ee"><div class="kpi-top"><span class="kpi-label"><span class="kpi-icon">${icon("calendar")}</span>Total taxe ${state.month.slice(0, 4)}</span></div>
        <div class="kpi-value" data-count="${yearTaxes}"></div><div class="kpi-foot"><span class="sub">de la începutul anului</span></div></article>
    </section>

    ${d.current.vat ? `
    <section class="card glass mt vat-card">
      <div class="card-head"><div><h2>TVA — decont ${esc(monthLabel(state.month))}</h2>
        <p>TVA nu e un cost al firmei: o încasați de la clienți și o dați statului, minus TVA plătită furnizorilor. Cota standard: ${rateTxt(settings.vat_standard_rate)}%.</p></div></div>
      <div class="vat-flow">
        <div class="vat-box in"><span>TVA colectată de la clienți</span><strong>${lei(d.current.vat.collected, true)}</strong><small>${rateTxt(settings.vat_standard_rate)}% din ${lei(d.current.revenue)}</small></div>
        <div class="vat-op">−</div>
        <div class="vat-box out"><span>TVA plătită pe marfă</span><strong>${lei(d.current.vat.deductible_purchases, true)}</strong><small>din achizițiile de ${lei(d.current.purchases)}</small></div>
        <div class="vat-op">−</div>
        <div class="vat-box out"><span>TVA plătită pe cheltuieli</span><strong>${lei(d.current.vat.deductible_expenses, true)}</strong><small>chirie, utilități, servicii…</small></div>
        <div class="vat-op">=</div>
        <div class="vat-box total ${d.current.vat.payable < 0 ? "refund" : ""}"><span>${d.current.vat.payable >= 0 ? "TVA de plată la stat" : "TVA de recuperat"}</span><strong>${lei(Math.abs(d.current.vat.payable), true)}</strong><small>până pe 25 luna următoare</small></div>
      </div>
    </section>` : ""}

    <section class="grid cols-2-even mt">
      <article class="card glass">
        <div class="card-head"><div><h2>Ce taxe plătiți, pe înțeles</h2><p>${esc(monthLabel(state.month))}</p></div></div>
        <div class="tax-explain">${explain.map(([abbr, color, name, text, value]) => `
          <div class="tax-item"><span class="ic" style="background:${color}22;color:${color}">${abbr}</span>
          <div><h4>${name}</h4><p>${esc(text)}</p></div><strong>${lei(value)}</strong></div>`).join("")}
        </div>
      </article>
      <article class="card glass">
        <div class="card-head"><div><h2>Din 100 lei salariu brut</h2><p>Cât ajunge la angajat și cât la stat</p></div></div>
        <div class="split">
          <div style="flex:${sample.net};background:#22d3ee">Net ${numberFmt2.format(sample.net)}</div>
          <div style="flex:${sample.cas};background:#a78bfa">CAS ${numberFmt.format(sample.cas)}</div>
          <div style="flex:${sample.cass};background:#34d399">CASS</div>
          <div style="flex:${sample.income_tax};background:#38bdf8">Imp.</div>
        </div>
        <p class="muted" style="font-size:13px;margin:0 0 18px">Pentru fiecare 100 lei brut, angajatul primește <b style="color:var(--text)">${numberFmt2.format(sample.net)} lei</b>, iar firma mai plătește <b style="color:var(--text)">${numberFmt2.format(sample.cam)} lei</b> CAM. Costul real al unui salariu este brutul + CAM.</p>
        <div class="card-head" style="margin-bottom:8px"><div><h3>Taxe lunare</h3></div></div>
        <div class="chart-box sm"><canvas id="tax-chart"></canvas></div>
      </article>
    </section>`;

  $$("[data-count]", view).forEach((el) => countUp(el, Number(el.dataset.count), el.dataset.suffix || " lei"));
  makeChart($("#tax-chart"), {
    type: "bar",
    data: {
      labels: d.trend.map((m) => m.label),
      datasets: [
        { label: "Taxe din salarii", data: d.trend.map((m) => m.salary_taxes), backgroundColor: "#a78bfa", borderRadius: 6, stack: "t", maxBarThickness: 20 },
        { label: d.current.company_tax_label, data: d.trend.map((m) => m.company_tax), backgroundColor: "#fbbf24", borderRadius: 6, stack: "t", maxBarThickness: 20 },
        ...(d.current.vat ? [{ label: "TVA de plată", data: d.trend.map((m) => m.vat_payable), backgroundColor: "#38bdf8", borderRadius: 6, stack: "v", maxBarThickness: 20 }] : []),
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { usePointStyle: true, pointStyle: "rectRounded" } },
        tooltip: { mode: "index", intersect: false, callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${lei(ctx.parsed.y)}` } } },
      scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, ticks: { callback: moneyTick } } },
    },
  });
}

/* ================= Rapoarte ================= */

async function renderReports(view) {
  const d = await api(`/api/dashboard?month=${state.month}`);
  const c = d.current;
  // Aceeași structură ca în raportul contabilului (contul de profit și pierdere).
  const rows = [
    ["Venituri din vânzări", c.revenue, "var(--cyan)"],
    ["Costul mărfii vândute", -c.cogs],
    ["Marja brută", c.gross_margin, "var(--violet)", `${pct(c.gross_margin_pct)}`],
    ...Object.entries(c.expenses_by_category).map(([name, value]) => [`&nbsp;&nbsp;&nbsp;${esc(name)}`, -value]),
    ["&nbsp;&nbsp;&nbsp;Salarii brute", -c.payroll.gross], ["&nbsp;&nbsp;&nbsp;CAM (contribuție angajator)", -c.taxes.cam],
    ["Total cheltuieli operaționale", -c.opex_total, "var(--text)"],
    ["Profit înainte de impozit", c.profit_before_tax, "var(--text)"],
    [c.company_tax_label, -c.taxes.company_tax],
    ["Profit net", c.profit, c.profit >= 0 ? "var(--green)" : "var(--red)", `marjă ${pct(c.margin)}`],
    ["Impozit pe dividende (estimat)", -c.dividend_tax], ["Rămâne proprietarului", c.owner_income, "var(--gold)"],
  ];
  const controls = [
    ["Achiziții marfă (fără TVA)", lei(c.purchases, true)], ["Valoare stoc la final de lună", lei(c.stock_value, true)],
    ...(c.vat ? [["TVA de plată", lei(c.vat.payable, true)]] : []),
    ["Salarii nete de plată", lei(c.payroll.net, true)],
    ["Contribuții și impozit salarii (CAS+CASS+impozit+CAM)", lei(c.taxes.cas + c.taxes.cass + c.taxes.income_tax + c.taxes.cam, true)],
    ["Creanțe clienți neîncasate (cu TVA, azi)", lei(d.receivables.total, true)], ["Număr facturi emise", c.sales_count],
  ];
  const year = d.trend;
  const sum = (k) => year.reduce((s, m) => s + m[k], 0);

  view.innerHTML = `
    <section class="grid cols-2-even">
      <button class="card glass export-card" id="exp-excel" type="button">
        <span class="ic" style="background:rgba(52,211,153,.15);color:var(--green)">${icon("excel")}</span>
        <div><h3>Descarcă Excel</h3><p>Raport ${esc(c.label)} pentru contabil: cont de profit și pierdere, TVA, vânzări, achiziții, cheltuieli, stocuri, salarii.</p></div>
      </button>
      <button class="card glass export-card" id="exp-pdf" type="button">
        <span class="ic" style="background:rgba(248,113,113,.15);color:var(--red)">${icon("pdf")}</span>
        <div><h3>Descarcă PDF</h3><p>Raport lunar gata de trimis contabilei sau de printat.</p></div>
      </button>
    </section>

    <section class="grid cols-2-even mt" style="align-items:start">
      <article class="card glass" id="closing-card"><div class="skeleton" style="height:180px"></div></article>
      <article class="card glass" id="audit-card"><div class="skeleton" style="height:180px"></div></article>
    </section>

    <section class="grid cols-2-even mt" style="align-items:start">
      <article class="card glass">
        <div class="card-head"><div><h2>Contul de profit și pierdere — ${esc(c.label)}</h2><p>Aceeași structură ca raportul contabilului</p></div></div>
        <div class="table-wrap"><table><tbody>
          ${rows.map(([name, value, color, note]) => `<tr><td${color ? ' style="font-weight:700"' : ""}>${name}${note ? ` <small class="muted">${note}</small>` : ""}</td>
            <td class="r" style="${color ? `color:${color};font-weight:800;font-size:15px` : "color:var(--muted)"}">${value < 0 ? "− " : ""}${lei(Math.abs(value), true)}</td></tr>`).join("")}
        </tbody></table></div>
        <h3 style="font-size:14px;margin:22px 0 6px">Indicatori de control</h3>
        <div class="table-wrap"><table class="compact"><tbody>
          ${controls.map(([name, value]) => `<tr><td>${name}</td><td class="r"><b>${value}</b></td></tr>`).join("")}
        </tbody></table></div>
      </article>
      <article class="card glass">
        <div class="card-head"><div><h2>Evoluție lunară</h2><p>Comparație lună de lună</p></div></div>
        <div class="table-wrap"><table class="compact">
          <thead><tr><th>Luna</th><th class="r">Venituri</th><th class="r">Costuri</th><th class="r">Profit</th><th class="r">Marjă</th></tr></thead>
          <tbody>${year.slice().reverse().map((m) => `<tr${m.month === state.month ? ' style="background:rgba(34,211,238,.07)"' : ""}>
            <td style="white-space:nowrap">${esc(m.label)}</td><td class="r">${lei(m.revenue)}</td><td class="r">${lei(m.costs)}</td>
            <td class="r" style="color:${m.profit >= 0 ? "var(--green)" : "var(--red)"};font-weight:700">${lei(m.profit)}</td>
            <td class="r">${m.revenue ? pct((m.profit / m.revenue) * 100) : "—"}</td></tr>`).join("")}</tbody>
          <tfoot><tr><td>Total</td><td class="r">${lei(sum("revenue"))}</td><td class="r">${lei(sum("costs"))}</td><td class="r">${lei(sum("profit"))}</td>
            <td class="r">${sum("revenue") ? pct((sum("profit") / sum("revenue")) * 100) : "—"}</td></tr></tfoot>
        </table></div>
      </article>
    </section>`;

  const download = (type) => {
    const a = document.createElement("a");
    a.href = `/api/export/${type}?month=${state.month}`;
    a.download = `raport-${state.month}.${type === "excel" ? "xlsx" : "pdf"}`;
    document.body.append(a); a.click(); a.remove();
    toast(`Se descarcă raportul ${type === "excel" ? "Excel" : "PDF"}…`);
  };
  $("#exp-excel").addEventListener("click", () => download("excel"));
  $("#exp-pdf").addEventListener("click", () => download("pdf"));
  mountClosing($("#closing-card"));
  mountAudit($("#audit-card"));
}

// Închiderea lunii: verificări, apoi blocarea modificărilor pe luna trimisă la contabil.
async function mountClosing(card) {
  const d = await api(`/api/closing?month=${state.month}`);
  const closedInfo = d.closed.find((c) => c.month === state.month);
  card.innerHTML = `
    <div class="card-head"><div><h2>${icon("lock")} Închiderea lunii — ${esc(monthLabel(state.month))}</h2>
      <p>După ce trimiteți raportul la contabil, închideți luna: nimeni nu mai poate modifica din greșeală facturile sau cheltuielile din ea.</p></div></div>
    ${d.is_closed ? `
      <div class="insight good"><span class="ic">${icon("lock")}</span><span>Luna este <b>închisă</b> din ${esc(closedInfo.closed_at.slice(0, 16).replace("T", " "))}.
        Profit la închidere: <b>${lei(closedInfo.snapshot.profit)}</b>, TVA: <b>${lei(closedInfo.snapshot.vat_payable)}</b>.</span></div>
      <div class="form-actions"><button class="btn btn-ghost" id="reopen-month" type="button">Redeschide luna</button></div>`
    : d.can_close ? `
      <ul class="checklist">${d.checklist.map((i) => `<li class="${i.ok ? "ok" : "warn"}">${icon(i.ok ? "check" : "alert")}<span>${esc(i.text)}</span></li>`).join("")}</ul>
      <div class="form-actions"><button class="btn btn-primary" id="close-month" type="button">${icon("lock")}Închide ${esc(monthLabel(state.month))}</button></div>`
    : `<p class="muted">Luna e încă în curs. Se poate închide după ce se termină.</p>`}
    ${d.closed.length ? `<p class="muted" style="font-size:12.5px;margin-top:14px">Luni închise: ${d.closed.map((c) => esc(monthLabel(c.month))).join(", ")}</p>` : ""}`;
  $("#close-month", card)?.addEventListener("click", async () => {
    const warnings = d.checklist.filter((i) => !i.ok).length;
    if (!await confirmBox(`Închideți ${monthLabel(state.month)}?`, `${warnings ? `Mai sunt ${warnings} verificări cu semne de întrebare. ` : ""}După închidere, documentele din lună nu se mai pot modifica (se poate redeschide oricând). Se face și o copie de siguranță.`, "Închide luna")) return;
    try { await api(`/api/closing/${state.month}`, { method: "POST" }); toast("Luna a fost închisă. Am făcut și o copie de siguranță."); render(); }
    catch (err) { toast(err.message, "err"); }
  });
  $("#reopen-month", card)?.addEventListener("click", async () => {
    if (!await confirmBox("Redeschideți luna?", "Documentele vor putea fi modificate din nou. Dacă ați trimis deja raportul, anunțați contabilul despre corecturi.", "Redeschide")) return;
    try { await api(`/api/closing/${state.month}`, { method: "DELETE" }); toast("Luna a fost redeschisă."); render(); }
    catch (err) { toast(err.message, "err"); }
  });
}

const AUDIT_ICONS = { insert: "plus", update: "edit", delete: "trash", event: "history" };

async function mountAudit(card, limit = 12) {
  const entries = await api(`/api/audit?limit=${limit}`);
  card.innerHTML = `
    <div class="card-head"><div><h2>${icon("history")} Jurnal de modificări</h2><p>Tot ce s-a adăugat, modificat sau șters, cu valorile vechi și noi.</p></div>
      ${limit < 500 ? '<button class="btn btn-sm" id="audit-all" type="button">Tot jurnalul</button>' : ""}</div>
    ${entries.length ? `<ul class="audit">${entries.map((e) => `
      <li class="audit-${e.action}"><span class="ic">${icon(AUDIT_ICONS[e.action] || "history")}</span>
        <div><b>${esc(e.text)}</b>${e.details.length ? `<small>${e.details.map(esc).join(" · ")}</small>` : ""}</div>
        <time>${esc(formatDate(e.at.slice(0, 10)))} ${esc(e.at.slice(11, 16))}</time></li>`).join("")}</ul>` : emptyState("Nicio modificare încă.")}`;
  $("#audit-all", card)?.addEventListener("click", () => {
    openModal("Jurnal de modificări", '<div id="audit-full" class="audit-modal"></div>', (body) => mountAudit($("#audit-full", body), 500));
  });
}

/* ================= Setări ================= */

async function renderSettings(view) {
  const [s, f, ai] = await Promise.all([api("/api/settings"), api("/api/fiscal"), api("/api/ai/status"), loadCategories()]);
  state.ai = ai;
  const statusText = f.last_check
    ? `Ultima verificare: ${new Date(f.last_check).toLocaleString("ro-RO", { dateStyle: "medium", timeStyle: "short" })} · ${f.last_status === "ok" ? "la zi" : "nu am putut verifica online, folosesc ultimele reguli salvate"}`
    : "Încă nu s-a făcut nicio verificare online.";

  view.innerHTML = `
    <section class="grid cols-2-even" style="align-items:start">
      <div class="grid">
        <article class="card glass">
          <div class="card-head"><div><h2>Firma</h2><p>Datele folosite în aplicație și în rapoarte.</p></div></div>
          <form id="settings-form">
            <div class="form-grid">
              <label class="field"><span>Numele firmei</span><input name="company_name" required maxlength="120" value="${esc(s.company_name)}"></label>
              <label class="field"><span>Numele dumneavoastră</span><input name="owner_name" maxlength="60" value="${esc(s.owner_name)}"><small>Așa vă salută asistentul.</small></label>
              <label class="field" style="grid-column:1/-1"><span>Regim de impozitare</span><select name="tax_regime">
                <option value="profit" ${s.tax_regime === "profit" ? "selected" : ""}>Impozit pe profit (16% din profit)</option>
                <option value="micro" ${s.tax_regime === "micro" ? "selected" : ""}>Microîntreprindere (% din venituri)</option>
              </select></label>
              <label class="check" style="grid-column:1/-1"><input type="checkbox" name="vat_payer" ${s.vat_payer === "1" ? "checked" : ""}><span>Firma este plătitoare de TVA (calculează TVA colectată, deductibilă și de plată)</span></label>
              <label class="field"><span>Ziua de plată a salariilor</span><input type="number" name="payday" min="1" max="28" step="1" value="${esc(s.payday || 10)}"><small>Pentru calendar și prognoza de bani.</small></label>
              <label class="field"><span>Pierdere fiscală de recuperat (lei)</span><input type="number" name="tax_loss_carried" min="0" step="1" value="${esc(s.tax_loss_carried || 0)}"><small>Din anii dinaintea datelor din aplicație (o aflați de la contabil).</small></label>
            </div>
            <div class="form-actions"><button class="btn btn-primary" type="submit">${icon("check")}Salvează</button></div>
          </form>
        </article>

        <article class="card glass fiscal-card">
          <div class="card-head">
            <div><h2>Legislație fiscală <span class="live-dot"></span></h2><p>Cotele se actualizează automat. Nu trebuie să faceți nimic.</p></div>
            <button class="btn btn-sm" id="fiscal-check" type="button">${icon("refresh")}Verifică acum</button>
          </div>
          <p class="muted" style="font-size:13px;margin:0 0 14px" id="fiscal-status">${esc(statusText)}</p>
          <div class="rates-grid">
            ${Object.entries(f.labels).map(([key, label]) => `
              <div class="rate"><span>${esc(label)}</span><strong>${rateTxt(f.current.rates[key])}%</strong></div>`).join("")}
          </div>
          <p class="muted" style="font-size:12px;margin:12px 0 18px">În vigoare din ${formatDate(f.current.effective_from)} · Sursa: ${esc(f.current.source)}${f.version ? ` · versiunea ${esc(f.version)}` : ""}</p>
          <h3 style="font-size:14px;margin:0 0 10px">Istoricul modificărilor</h3>
          <ul class="law-timeline">
            ${f.history.map((r) => `
              <li class="${r.effective_from > todayISO() ? "future" : ""}">
                <b>${formatDate(r.effective_from)}</b> — ${esc(r.title)}${r.effective_from > todayISO() ? ' <span class="tag order">urmează</span>' : ""}
                ${r.changes.length ? `<ul>${r.changes.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>` : ""}
              </li>`).join("")}
          </ul>
        </article>
      </div>

      <div class="grid">
        <article class="card glass">
          <div class="card-head"><div><h2>Schimbă parola</h2><p>Doar dumneavoastră aveți acces la aplicație.</p></div></div>
          <form id="password-form" class="form-grid">
            <label class="field"><span>Parola actuală</span><input type="password" name="current" required autocomplete="current-password"></label>
            <label class="field"><span>Parola nouă</span><input type="password" name="new" required minlength="4" autocomplete="new-password"></label>
            <div class="form-actions" style="grid-column:1/-1;margin-top:0"><button class="btn" type="submit">${icon("check")}Schimbă parola</button></div>
          </form>
          <div class="recovery-status ${state.hasRecovery ? "" : "missing"}">
            <span>${icon(state.hasRecovery ? "check" : "alert")}</span>
            <div><b>Cod de recuperare</b><small>${state.hasRecovery
              ? "Aveți un cod activ. Dacă l-ați pierdut, generați unul nou (cel vechi nu mai merge)."
              : "Nu aveți încă un cod. Fără el, dacă uitați parola nu mai puteți intra."}</small></div>
            <button class="btn btn-sm ${state.hasRecovery ? "" : "btn-gold"}" id="recovery-btn" type="button">${state.hasRecovery ? "Cod nou" : "Generează"}</button>
          </div>
        </article>
        <article class="card glass">
          <div class="card-head"><div><h2>Categorii de cheltuieli</h2><p>${state.categories.length} categorii</p></div>
            <button class="btn btn-sm" id="cats-btn" type="button">${icon("edit")}Gestionează</button></div>
          <div class="toolbar">${state.categories.map((c) => `<span class="tag"><span class="sw" style="background:${esc(c.color)}"></span>${esc(c.name)}</span>`).join("")}</div>
        </article>
        <article class="card glass ai-card">
          <div class="card-head"><div><h2>Testi cu inteligență artificială <span class="tag ${ai.enabled ? "paid" : ""}">${ai.enabled ? "activ" : "oprit"}</span></h2>
            <p>Opțional: puneți întrebări libere despre firmă („De ce a scăzut profitul?”), iar Testi răspunde folosind Claude (Anthropic).</p></div></div>
          <form id="ai-form">
            <label class="check"><input type="checkbox" name="enabled" ${ai.switched_on ? "checked" : ""}><span>Activează asistentul AI</span></label>
            <label class="field" style="margin-top:12px"><span>Cheie API Anthropic</span>
              <input type="password" name="api_key" autocomplete="off" placeholder="${ai.key_hint ? esc(ai.key_hint) + " (salvată)" : ai.key_source ? "din " + esc(ai.key_source) : "sk-ant-…"}">
              <small>O obțineți din contul Anthropic (console.anthropic.com). Lăsați gol ca să păstrați cheia salvată.</small></label>
            <div class="preview ai-consent">
              <b>Ce trebuie să știți:</b>
              <ul>
                <li>La fiecare întrebare, cifrele firmei (vânzări, stoc, clienți, furnizori, salarii) se trimit la Anthropic ca să se genereze răspunsul. Parola și cheia nu se trimit.</li>
                <li>Are nevoie de internet, iar fiecare întrebare costă câțiva bani din contul Anthropic.</li>
                <li>Fără cheie, aplicația rămâne complet locală.</li>
              </ul>
            </div>
            <div class="form-actions">
              ${ai.key_hint ? `<button class="btn btn-ghost" type="button" id="ai-clear">${icon("trash")}Șterge cheia</button>` : ""}
              <button class="btn btn-primary" type="submit">${icon("check")}Salvează</button>
            </div>
          </form>
        </article>
        <article class="card glass import-card">
          <div class="card-head"><div><h2>Import din Excel / CSV</h2><p>Aduceți datele din fișierele folosite până acum: produse, clienți, angajați, vânzări, cheltuieli, inventar sau raportul contabil.</p></div></div>
          <form id="import-form">
            <label class="dropzone" id="dropzone">
              <input type="file" name="files" multiple accept=".csv,.xlsx" hidden>
              ${icon("excel")}<b>Alegeți fișierele</b><span>sau trageți-le aici · .xlsx sau .csv</span>
              <span class="files" id="import-files"></span>
            </label>
            <label class="check" style="margin-top:12px"><input type="checkbox" name="replace"><span>Înlocuiește datele existente (altfel se adaugă doar ce lipsește)</span></label>
            <div class="form-actions"><button class="btn btn-primary" type="submit" id="import-btn">${icon("refresh")}Importă</button></div>
            <div id="import-result"></div>
          </form>
        </article>
        <article class="card glass" id="backup-card"><div class="skeleton" style="height:160px"></div></article>
        <article class="card glass" style="border-color:rgba(248,113,113,.3)">
          <div class="card-head"><div><h2>Datele firmei T3 2026</h2><p>Înlocuiește TOATE datele cu fișierele primite de la firmă (raportul contabil iulie–septembrie 2026).</p></div></div>
          <button class="btn btn-danger" id="demo-btn" type="button">${icon("alert")}Reîncarcă datele firmei</button>
        </article>
      </div>
    </section>`;

  $("#settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const d = formData(e.target);
    const body = { company_name: d.company_name, owner_name: d.owner_name, tax_regime: d.tax_regime, vat_payer: $("[name=vat_payer]", e.target).checked,
      payday: Number(d.payday) || 10, tax_loss_carried: Number(d.tax_loss_carried) || 0 };
    try {
      await api("/api/settings", { method: "PUT", body });
      $("#brand-name").textContent = body.company_name;
      state.ownerName = body.owner_name;
      toast("Setările au fost salvate.");
    } catch (err) { toast(err.message, "err"); }
  });
  $("#fiscal-check").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.classList.add("spinning");
    try {
      const result = await api("/api/fiscal/check", { method: "POST" });
      toast(result.message, result.ok ? "ok" : "err");
      if (result.changed.length) { robot.refresh(); }
      render();
    } catch (err) { toast(err.message, "err"); btn.disabled = false; btn.classList.remove("spinning"); }
  });
  $("#password-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/api/auth/change-password", { method: "POST", body: formData(e.target) });
      e.target.reset(); toast("Parola a fost schimbată.");
    } catch (err) { toast(err.message, "err"); }
  });
  $("#cats-btn").addEventListener("click", () => openCategories(render));
  wireImport(view);
  const saveAI = async (body) => {
    try {
      state.ai = await api("/api/ai/settings", { method: "PUT", body });
      robot.renderAsk();
      toast(state.ai.enabled ? "Asistentul AI e activ. Întrebați-l pe Testi din colțul din dreapta jos." : "Setările AI au fost salvate.");
      render();
    } catch (err) { toast(err.message, "err"); }
  };
  $("#ai-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const enabled = e.target.enabled.checked, key = e.target.api_key.value.trim();
    if (enabled && !key && !state.ai.has_key) { toast("Introduceți cheia API ca să porniți asistentul.", "err"); return; }
    saveAI({ enabled, api_key: key || null });
  });
  $("#ai-clear")?.addEventListener("click", () => saveAI({ enabled: false, clear_key: true }));
  $("#recovery-btn").addEventListener("click", () => {
    openModal("Cod de recuperare nou", `<form id="recovery-form">
      <p class="muted" style="margin-top:0">Pentru siguranță, confirmați parola actuală. Codul vechi nu va mai funcționa.</p>
      <label class="field"><span>Parola actuală</span><input type="password" name="current" required autocomplete="current-password"></label>
      <div class="form-actions"><button class="btn btn-ghost" type="button" onclick="closeModal()">Renunță</button>
      <button class="btn btn-primary" type="submit">Generează codul</button></div></form>`, (body) => {
      $("#recovery-form", body).addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          const { recovery_code: code } = await api("/api/auth/recovery-code", { method: "POST", body: formData(e.target) });
          state.hasRecovery = true;
          $("#modal-title").textContent = "Notați noul cod de recuperare";
          mountRecoveryCode(body, code, "Gata", () => { closeModal(); render(); });
        } catch (err) { toast(err.message, "err"); }
      });
    });
  });
  $("#demo-btn").addEventListener("click", async () => {
    if (await confirmBox("Reîncărcați datele firmei?", "Toate datele actuale vor fi înlocuite cu cele din raportul contabil T3 2026.", "Da, înlocuiește")) {
      try { await api("/api/demo", { method: "POST" }); toast("Datele firmei au fost încărcate."); state.month = "2026-09"; location.hash = "#dashboard"; render(); }
      catch (err) { toast(err.message, "err"); }
    }
  });
  mountBackups($("#backup-card"));
}

const fileSize = (bytes) => bytes > 1048576 ? `${(bytes / 1048576).toFixed(1).replace(".", ",")} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;

// Copii de siguranță: zilnic automat; restaurare dintr-o copie sau din exportul complet.
async function mountBackups(card) {
  const d = await api("/api/backups");
  const label = (name) => name.includes("inainte-de") ? "înainte de restaurare / demo" : name.includes("inchidere") ? "la închiderea lunii" : name.includes("manual") ? "manuală" : "automată";
  card.innerHTML = `
    <div class="card-head"><div><h2>${icon("shield")} Copii de siguranță</h2>
      <p>Aplicația face singură o copie în fiecare zi și păstrează ultimele ${d.keep}. Pentru siguranță deplină, descărcați lunar exportul complet pe un stick sau în cloud.</p></div></div>
    <div class="form-actions" style="justify-content:flex-start;flex-wrap:wrap;margin-top:0">
      <button class="btn btn-primary" id="backup-now" type="button">${icon("shield")}Fă o copie acum</button>
      <a class="btn" href="/api/export/full" download>${icon("excel")}Export complet (ZIP)</a>
      <label class="btn btn-ghost" style="cursor:pointer">${icon("refresh")}Restaurează din fișier<input type="file" id="restore-file" accept=".zip,.db" hidden></label>
    </div>
    ${d.backups.length ? `<div class="table-wrap mt"><table class="compact"><thead><tr><th>Copie</th><th>Tip</th><th class="r">Mărime</th><th></th></tr></thead><tbody>
      ${d.backups.slice(0, 8).map((b) => `<tr><td>${esc(formatDate(b.created.slice(0, 10)))} ${esc(b.created.slice(11, 16))}</td><td><span class="tag">${label(b.name)}</span></td>
        <td class="r">${fileSize(b.size)}</td><td class="actions"><button class="btn btn-sm" data-restore="${esc(b.name)}" type="button">Restaurează</button></td></tr>`).join("")}
    </tbody></table></div>` : ""}
    <p class="muted" style="font-size:12px;margin-top:10px">Folder: <span class="mono">${esc(d.folder)}</span></p>`;
  const restored = (r) => { toast(`Datele au fost restaurate. Starea de dinainte e salvată ca „${r.safety_backup}”.`); render(); };
  $("#backup-now", card).addEventListener("click", async () => {
    try { await api("/api/backups", { method: "POST" }); toast("Copia de siguranță a fost făcută."); mountBackups(card); }
    catch (err) { toast(err.message, "err"); }
  });
  card.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-restore]");
    if (!btn) return;
    if (!await confirmBox("Restaurați această copie?", "Datele de acum vor fi înlocuite cu cele din copie. Înainte, aplicația salvează automat starea actuală, ca să puteți reveni.", "Restaurează")) return;
    try { restored(await api(`/api/backups/${encodeURIComponent(btn.dataset.restore)}/restore`, { method: "POST" })); }
    catch (err) { toast(err.message, "err"); }
  });
  $("#restore-file", card).addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file || !await confirmBox("Restaurați din fișier?", `Datele de acum vor fi înlocuite cu cele din „${file.name}”. Starea actuală se salvează automat înainte.`, "Restaurează")) return;
    const form = new FormData();
    form.append("file", file);
    try { restored(await api("/api/backups/upload", { method: "POST", body: form })); }
    catch (err) { toast(err.message, "err"); }
  });
}

const IMPORT_LABELS = { clients: "clienți", products: "produse", stock: "stocuri inițiale", purchases: "recepții",
  sales: "facturi", expenses: "cheltuieli", employees: "angajați" };

function wireImport(view) {
  const form = $("#import-form", view);
  const input = $("[name=files]", form), zone = $("#dropzone", form);
  const show = () => { $("#import-files", form).textContent = [...input.files].map((f) => f.name).join(", "); };
  input.addEventListener("change", show);
  ["dragover", "dragenter"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, () => zone.classList.remove("over")));
  zone.addEventListener("drop", (e) => { e.preventDefault(); input.files = e.dataTransfer.files; show(); });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!input.files.length) { toast("Alegeți cel puțin un fișier.", "err"); return; }
    const data = new FormData();
    [...input.files].forEach((f) => data.append("files", f));
    data.append("replace", $("[name=replace]", form).checked ? "true" : "false");
    const btn = $("#import-btn", form);
    btn.disabled = true; btn.classList.add("spinning");
    try {
      const res = await fetch("/api/import", { method: "POST", body: data, credentials: "same-origin" });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || "Importul nu a reușit.");
      const parts = Object.entries(result.counts).map(([k, n]) => `<li><b>${n}</b> ${IMPORT_LABELS[k] || k}</li>`);
      $("#import-result", form).innerHTML = `<div class="preview"><b>Import reușit.</b>
        ${parts.length ? `<ul>${parts.join("")}</ul>` : "<p class='muted'>Nimic nou: datele existau deja.</p>"}
        ${result.warnings.map((w) => `<p class="muted">${esc(w)}</p>`).join("")}</div>`;
      toast("Datele au fost importate.");
      robot.refresh();
    } catch (err) {
      $("#import-result", form).innerHTML = `<p class="error">${esc(err.message)}</p>`;
    } finally { btn.disabled = false; btn.classList.remove("spinning"); }
  });
}

/* ================= Asistentul Testi ================= */

// Fiecare robot desenat are id-uri proprii pentru gradienți: dacă două desene ar folosi aceleași
// id-uri, cel din panoul ascuns ar lăsa butonul fără culori.
let robotCount = 0;
function robotSVG(className = "") {
  const id = `rb${++robotCount}`;
  return `<svg class="robot ${className}" viewBox="0 0 120 120" aria-hidden="true">
    <defs>
      <linearGradient id="${id}-body" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1e293b"/><stop offset="1" stop-color="#0b1222"/></linearGradient>
      <linearGradient id="${id}-edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#3b82f6"/></linearGradient>
      <radialGradient id="${id}-eye"><stop offset="0" stop-color="#ecfeff"/><stop offset=".45" stop-color="#22d3ee"/><stop offset="1" stop-color="#0891b2" stop-opacity="0"/></radialGradient>
    </defs>
    <g class="rb-antenna"><line x1="60" y1="14" x2="60" y2="26" stroke="url(#${id}-edge)" stroke-width="3"/><circle class="rb-light" cx="60" cy="11" r="5" fill="#fbbf24"/></g>
    <rect x="24" y="26" width="72" height="54" rx="20" fill="url(#${id}-body)" stroke="url(#${id}-edge)" stroke-width="3"/>
    <rect x="33" y="37" width="54" height="30" rx="13" fill="#020617"/>
    <g class="rb-eyes"><circle cx="48" cy="52" r="7" fill="url(#${id}-eye)"/><circle cx="72" cy="52" r="7" fill="url(#${id}-eye)"/></g>
    <path class="rb-mouth" d="M52 61 q8 5 16 0" stroke="#22d3ee" stroke-width="2.5" fill="none" stroke-linecap="round"/>
    <rect x="18" y="45" width="6" height="16" rx="3" fill="#22d3ee"/><rect x="96" y="45" width="6" height="16" rx="3" fill="#22d3ee"/>
    <rect x="40" y="82" width="40" height="26" rx="10" fill="url(#${id}-body)" stroke="url(#${id}-edge)" stroke-width="3"/>
    <circle cx="60" cy="95" r="4" fill="#fbbf24"/>
    <g class="rb-arm"><path d="M80 88 q16 -4 20 -20" stroke="url(#${id}-edge)" stroke-width="5" fill="none" stroke-linecap="round"/><circle cx="100" cy="66" r="5" fill="#22d3ee"/></g>
    <path d="M40 90 q-12 4 -14 16" stroke="url(#${id}-edge)" stroke-width="5" fill="none" stroke-linecap="round"/>
  </svg>`;
}

const robot = {
  messages: [],
  actions: [],
  playing: 0,

  chat: [],  // conversația cu AI-ul: [{role, content}]

  init() {
    $("#assistant").classList.remove("hidden");
    api("/api/ai/status").then((st) => { state.ai = st; this.renderAsk(); }).catch(() => {});
    $("#assistant-fab").innerHTML = `${robotSVG("mini")}<span class="fab-dot hidden" id="assistant-dot"></span>`;
    $("#assistant-avatar").innerHTML = robotSVG("waving");
    $("#assistant-fab").onclick = () => this.toggle();
    $("#assistant-close").onclick = () => this.close();
    let greeted = false;
    try { greeted = sessionStorage.getItem("testi-greeted") === "1"; } catch { /* stocare indisponibilă */ }
    this.refresh(!greeted);
    try { sessionStorage.setItem("testi-greeted", "1"); } catch { /* stocare indisponibilă */ }
  },

  toggle() { $("#assistant-panel").classList.contains("hidden") ? this.open() : this.close(); },
  close() { $("#assistant-panel").classList.add("hidden"); $("#assistant-fab").classList.remove("open"); },
  open() {
    $("#assistant-panel").classList.remove("hidden");
    $("#assistant-fab").classList.add("open");
    $("#assistant-dot").classList.add("hidden");
    this.play();
  },

  async refresh(autoOpen = false) {
    try {
      await this.compose();
      const hasNews = this.fiscalNews;
      if (autoOpen || hasNews) this.open();
      else $("#assistant-dot").classList.toggle("hidden", !hasNews);
    } catch { /* asistentul nu trebuie să blocheze aplicația */ }
  },

  async compose() {
    const lastMonth = shiftMonth(currentMonth(), -1);
    const [past, now, fiscalInfo] = await Promise.all([
      api(`/api/dashboard?month=${lastMonth}`), api(`/api/dashboard?month=${currentMonth()}`), api("/api/fiscal"),
    ]);
    const name = past.owner_name || state.ownerName || "";
    const p = past.current;
    const msgs = [];
    msgs.push({ html: `<b>${esc(greeting())}${name ? `, ${esc(name)}` : ""}!</b> Eu sunt <b>Testi</b>, asistentul tău financiar. Am pregătit cifrele firmei pentru tine.` });
    if (p.revenue) {
      msgs.push({ html: `În <b>${esc(p.label)}</b> ai încasat <b>${lei(p.revenue)}</b>, iar profitul net a fost <b class="${p.profit >= 0 ? "pos" : "neg"}">${lei(p.profit)}</b>. ${p.owner_income > 0 ? `Ție îți rămân <b class="gold">${lei(p.owner_income)}</b> după impozitul pe dividende.` : "Luna a fost pe pierdere, deci nu se plătește impozit pe profit."}` });
    }
    if (now.current.revenue) {
      const ch = now.changes.revenue;
      msgs.push({ html: `Luna aceasta, până azi: <b>${lei(now.current.revenue)}</b> încasări${ch !== null ? `, <b class="${ch >= 0 ? "pos" : "neg"}">${ch >= 0 ? "+" : "−"}${pct(Math.abs(ch))}</b> față de aceeași perioadă a lunii trecute` : ""}.` });
    }
    const overdue = now.receivables.clients.filter((x) => x.overdue);
    if (overdue.length) {
      msgs.push({ tone: "warn", html: `${icon("wallet")} Ai <b>${lei(now.receivables.overdue)}</b> de încasat de la clienți care au trecut de scadență: ${overdue.slice(0, 3).map((x) => `<b>${esc(x.client)}</b> (${lei(x.overdue)})`).join(", ")}. Merită un telefon.` });
    }
    if (now.low_stock.length) {
      msgs.push({ tone: "warn", html: `${icon("box")} Stoc pe terminate: ${now.low_stock.slice(0, 3).map((x) => `<b>${esc(x.name)}</b> (${x.stock} buc.)`).join(", ")}${now.low_stock.length > 3 ? ` și încă ${now.low_stock.length - 3}` : ""}. Fă o comandă la furnizori.` });
    }
    const pay = now.payables;
    if (pay.due_soon || pay.overdue) {
      msgs.push({ tone: "warn", html: `${icon("truck")} Plăți către furnizori: <b>${lei(pay.due_soon)}</b> scadente în 7 zile${pay.overdue ? ` și <b>${lei(pay.overdue)}</b> deja restante` : ""}. Ai de încasat ${lei(now.receivables.total)}, deci ${now.receivables.total >= pay.total ? "acoperi plățile din încasări." : "încasările nu acoperă toate plățile, ai grijă la cont."}` });
    }
    if (now.reminders?.length) {
      const total = now.reminders.reduce((s, r) => s + r.amount, 0);
      const first = now.reminders[0];
      msgs.push({ tone: "warn", html: `${icon("calendar")} <b>Memento:</b> ${first.days_left === 0 ? "azi" : first.days_left === 1 ? "mâine" : `în ${first.days_left} zile (${formatDate(first.date)})`} ai de plătit <b>${lei(total)}</b>: ${now.reminders.map((r) => `${esc(r.form)} ${lei(r.amount)}`).join(", ")}. Le găsești în Calendarul fiscal, unde le poți bifa după plată.` });
    } else if (p.vat) msgs.push({ html: `${icon("taxes")} Pentru ${esc(p.label)} ai de plătit <b>${lei(p.vat.payable)}</b> TVA, până pe 25 a lunii următoare.` });
    const g = now.goals;
    if (g?.revenue) {
      const ok = g.revenue.projected >= g.revenue.target;
      msgs.push({ tone: ok ? "" : "warn", html: `${icon("target")} Obiectivul lunii: <b>${lei(g.revenue.target)}</b> vânzări. Ești la <b>${pct(g.revenue.pct)}</b> și, în ritmul ăsta, ajungi la <b class="${ok ? "pos" : "neg"}">${lei(g.revenue.projected)}</b>${ok ? ". Bravo!" : `. Ar trebui cam <b>${lei(g.revenue.daily_needed)}</b> pe zi până la final de lună.`}` });
    }
    const warn = past.insights.find((n) => n.tone === "warn" || n.tone === "bad");
    if (warn) msgs.push({ html: `${icon("alert")} ${esc(warn.text)}`, tone: "warn" });

    this.fiscalNews = fiscalInfo.unseen.length > 0;
    if (this.fiscalNews) {
      fiscalInfo.unseen.forEach((rule) => {
        const future = rule.effective_from > todayISO();
        msgs.push({
          tone: "law",
          html: `<b>${icon("taxes")} Noutate în Codul fiscal</b> — ${esc(rule.title)} (${future ? "se aplică de la" : "în vigoare din"} ${formatDate(rule.effective_from)}).
            <ul>${rule.changes.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
            Am actualizat deja calculele. Nu trebuie să faci nimic.`,
        });
      });
    } else {
      const r = fiscalInfo.current.rates;
      const checked = fiscalInfo.last_check && fiscalInfo.last_status === "ok"
        ? ` (verificat ${new Date(fiscalInfo.last_check).toLocaleString("ro-RO", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })})` : "";
      msgs.push({ tone: "law", html: `${icon("check")} Regulile fiscale sunt la zi${esc(checked)}: impozit pe profit ${rateTxt(r.profit_tax_rate)}%, dividende ${rateTxt(r.dividend_tax_rate)}%. Te anunț eu dacă se schimbă ceva.` });
    }
    if (state.hasRecovery === false) {
      msgs.push({ tone: "warn", html: `${icon("alert")} Nu ai încă un <b>cod de recuperare</b> a parolei. Dacă o uiți, nu mai poți intra. Generează-l din Setări, durează 10 secunde.` });
    }
    this.messages = msgs;
    this.actions = [
      ...(this.fiscalNews ? [{ label: "Am înțeles", primary: true, run: async () => { await api("/api/fiscal/seen", { method: "POST" }); this.fiscalNews = false; toast("Mulțumesc! Am notat că ai văzut noutățile."); this.close(); } }] : []),
      { label: "Adaugă o vânzare", run: () => { this.close(); quickAdd("sale"); } },
      { label: "Calendar fiscal", run: () => { this.close(); location.hash = "#calendar"; } },
      { label: "Bani în cont", run: () => { this.close(); location.hash = "#bani"; } },
    ];
    this.rendered = false;
  },

  async play() {
    if (this.rendered) return;
    this.rendered = true;
    const run = ++this.playing;
    const box = $("#assistant-messages");
    const actions = $("#assistant-actions");
    box.innerHTML = "";
    actions.innerHTML = "";
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    for (const msg of this.messages) {
      const typing = document.createElement("div");
      typing.className = "bubble typing";
      typing.innerHTML = "<i></i><i></i><i></i>";
      box.append(typing);
      box.scrollTop = box.scrollHeight;
      await new Promise((r) => setTimeout(r, reduce ? 0 : 650));
      if (run !== this.playing) return;
      typing.className = `bubble ${msg.tone || ""}`;
      typing.innerHTML = msg.html;
      box.scrollTop = box.scrollHeight;
      await new Promise((r) => setTimeout(r, reduce ? 0 : 250));
    }
    this.actions.forEach((a) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `btn btn-sm ${a.primary ? "btn-primary" : ""}`;
      b.textContent = a.label;
      b.onclick = a.run;
      actions.append(b);
    });
    this.chat.forEach((m) => this.addBubble(m.role, m.content));
    this.renderAsk();
  },

  addBubble(role, text, extraClass = "") {
    const box = $("#assistant-messages");
    const el = document.createElement("div");
    el.className = `bubble ${role === "user" ? "me" : "ai"} ${extraClass}`;
    el.innerHTML = role === "user" ? esc(text) : renderMarkdown(text);
    box.append(el);
    box.scrollTop = box.scrollHeight;
    return el;
  },

  renderAsk() {
    const holder = $("#assistant-ask");
    if (!holder) return;
    if (!state.ai?.enabled) { holder.innerHTML = ""; return; }
    if (holder.childElementCount) return;
    const ideas = ["De ce a scăzut profitul în august?", "Ce produse ar trebui să comand?", "Cine îmi datorează cei mai mulți bani?"];
    holder.innerHTML = `
      <div class="ask-ideas">${ideas.map((q) => `<button type="button" class="tag order" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div>
      <form class="ask-form">
        <input name="q" maxlength="1000" autocomplete="off" placeholder="Întreabă-l pe Testi orice despre firmă…">
        <button class="btn btn-primary btn-sm" type="submit" aria-label="Trimite">${icon("up")}</button>
      </form>
      <small class="muted ask-note">${icon("star")} Răspunsuri generate cu AI (Claude) din cifrele firmei. Verificați deciziile importante.</small>`;
    const form = $(".ask-form", holder);
    $$("[data-q]", holder).forEach((b) => b.addEventListener("click", () => { form.q.value = b.dataset.q; form.requestSubmit(); }));
    form.addEventListener("submit", (e) => { e.preventDefault(); this.askAI(form); });
  },

  async askAI(form) {
    const question = form.q.value.trim();
    if (!question || this.thinking) return;
    form.q.value = "";
    this.thinking = true;
    form.querySelector("button").disabled = true;
    this.chat.push({ role: "user", content: question });
    this.addBubble("user", question);
    const typing = this.addBubble("assistant", "", "typing");
    typing.innerHTML = "<i></i><i></i><i></i>";
    try {
      const { reply } = await api("/api/ai/chat", { method: "POST", body: { messages: this.chat } });
      typing.remove();
      this.chat.push({ role: "assistant", content: reply });
      this.addBubble("assistant", reply);
    } catch (err) {
      typing.remove();
      this.chat.pop();  // întrebarea fără răspuns nu rămâne în istoric
      this.addBubble("assistant", err.message, "warn");
    } finally {
      this.thinking = false;
      form.querySelector("button").disabled = false;
      form.q.focus();
    }
  },
};

// Text simplu din răspunsul AI: **îngroșat**, liste cu „- ” și rânduri noi. Totul e escapat întâi.
function renderMarkdown(text) {
  const lines = esc(text).split("\n");
  let html = "", inList = false;
  for (const line of lines) {
    const item = line.match(/^\s*[-•*]\s+(.*)$/);
    if (item && !inList) { html += "<ul>"; inList = true; }
    if (!item && inList) { html += "</ul>"; inList = false; }
    html += item ? `<li>${item[1]}</li>` : (line.trim() ? `<p>${line}</p>` : "");
  }
  if (inList) html += "</ul>";
  return html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
}

/* ================= Adăugare rapidă (mai ales pe telefon) ================= */

async function quickAdd(kind = "sale") {
  await Promise.all([loadCategories(), loadCatalog()]);
  const body = (k) => `
    <div class="segmented" style="margin-bottom:16px">
      <button type="button" data-kind="sale" class="${k === "sale" ? "active" : ""}">Vânzare</button>
      <button type="button" data-kind="expense" class="${k === "expense" ? "active" : ""}">Cheltuială</button>
    </div>
    <form id="quick-form">${k === "sale" ? saleFormHTML({}, "order") : expenseFormHTML()}
      <div class="form-actions"><button class="btn btn-primary btn-block" type="submit">${icon("plus")}Salvează</button></div>
    </form>`;
  const mount = (root, k) => {
    $$("[data-kind]", root).forEach((b) => b.addEventListener("click", () => { root.innerHTML = body(b.dataset.kind); mount(root, b.dataset.kind); }));
    const form = $("#quick-form", root);
    if (k === "sale") wireSaleForm(form); else wireExpenseForm(form);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const payload = k === "sale" ? salePayload(form, "order") : expensePayload(form);
        const result = await api(k === "sale" ? "/api/sales" : "/api/expenses", { method: "POST", body: payload });
        if (result.warning) toast(result.warning, "err");
        closeModal();
        toast(k === "sale" ? `Factura ${result.invoice_number} a fost emisă.` : `Cheltuială salvată: ${lei(payload.amount, true)}`);
        setMonthFromDate(payload.date);
        render();
      } catch (err) { toast(err.message, "err"); }
    });
  };
  openModal("Adăugare rapidă", body(kind), (root) => mount(root, kind));
}
$("#quick-add").addEventListener("click", () => quickAdd("sale"));

/* ================= Aplicație instalabilă (PWA) ================= */

if ("serviceWorker" in navigator && window.isSecureContext) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/static/sw.js").catch(() => {}));
}

window.closeModal = closeModal;
boot();
