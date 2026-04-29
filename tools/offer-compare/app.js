import { fmtUSD, fmtPct, fmtNumber } from "./lib/format.js";
import { loadAll, saveAll, clearAll, exportJSON, importJSON,
         encodeStateToHash, decodeStateFromHash } from "./lib/storage.js";
import { summarize, DEFAULT_OFFER } from "./lib/comp.js";

// ─── Data load ──────────────────────────────────────────────────────────────
const [federalData, stateTaxData, localTaxData, beaData] = await Promise.all([
  fetch("./data/federal-2026.json").then(r => r.json()),
  fetch("./data/state-tax-2026.json").then(r => r.json()),
  fetch("./data/local-tax-2026.json").then(r => r.json()),
  fetch("./data/bea-rpp.json").then(r => r.json())
]);

// ─── State ──────────────────────────────────────────────────────────────────
const initialState = {
  offers: [],
  settings: { filingStatus: "mfj", discountRate: 0.05, horizonYears: 5 }
};

let state = decodeStateFromHash(location.hash) || loadAll() || initialState;
if (!state.offers) state.offers = [];
if (!state.settings) state.settings = initialState.settings;

function persist() {
  saveAll(state);
}

// ─── Element refs ───────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const offersList = $("#offers-list");
const comparison = $("#comparison");
const editor = $("#editor");
const editorForm = $("#editor-form");
const editorTitle = $("#editor-title");
const stateSel = $("#editor-state");
const locSel = $("#editor-location");
const localitySel = $("#editor-locality");

// ─── Populate dropdowns from data ───────────────────────────────────────────
function fillStateOptions() {
  const states = Object.entries(stateTaxData.states)
    .sort((a, b) => a[1].name.localeCompare(b[1].name));
  stateSel.innerHTML = states
    .map(([k, v]) => `<option value="${k}">${v.name}</option>`)
    .join("");
}

function fillLocationOptions(stateKey) {
  const metros = Object.entries(beaData.metros)
    .filter(([k, v]) => !stateKey || v.state === stateKey || k === "USAvg")
    .sort((a, b) => a[1].name.localeCompare(b[1].name));
  const stateOpt = stateTaxData.states[stateKey];
  const stateLine = stateOpt ? `<option value="${stateKey}">— ${stateOpt.name} (state avg) —</option>` : "";
  const metroLines = metros.map(([k, v]) => `<option value="${k}">${v.name}</option>`).join("");
  locSel.innerHTML = stateLine + metroLines;
}

function fillLocalityOptions(stateKey) {
  const localities = Object.entries(localTaxData.localities)
    .filter(([k, v]) => !stateKey || v.state === stateKey)
    .sort((a, b) => a[1].name.localeCompare(b[1].name));
  localitySel.innerHTML = `<option value="">— none —</option>` +
    localities.map(([k, v]) => `<option value="${k}">${v.name}</option>`).join("");
}

fillStateOptions();
fillLocationOptions();
fillLocalityOptions();

stateSel.addEventListener("change", () => {
  fillLocationOptions(stateSel.value);
  fillLocalityOptions(stateSel.value);
});

// ─── Form serialization (dotted names) ──────────────────────────────────────
function setNested(obj, path, value) {
  const parts = path.split(".");
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    if (cur[parts[i]] == null || typeof cur[parts[i]] !== "object") cur[parts[i]] = {};
    cur = cur[parts[i]];
  }
  cur[parts[parts.length - 1]] = value;
}
function getNested(obj, path) {
  return path.split(".").reduce((c, k) => (c == null ? undefined : c[k]), obj);
}

// Read a value from an input element with type-aware coercion.
function readInput(el) {
  if (el.type === "checkbox") return el.checked;
  if (el.type === "number")  return el.value === "" ? null : Number(el.value);
  return el.value;
}

function offerFromForm(form, base) {
  const o = JSON.parse(JSON.stringify(base)); // deep clone defaults
  for (const el of form.elements) {
    if (!el.name) continue;
    const path = el.name;
    const v = readInput(el);

    // Special-case: comma-separated baseYearly
    if (path === "cash.baseYearly") {
      o.cash.baseYearly = (v || "").toString()
        .split(",").map(s => s.trim()).filter(Boolean).map(Number);
      continue;
    }
    // Special-case: retention "year:amount, year:amount"
    if (path === "cash.retention") {
      o.cash.retention = (v || "").toString()
        .split(",").map(s => s.trim()).filter(Boolean)
        .map(pair => {
          const [yr, amt] = pair.split(":").map(s => s.trim());
          return { year: Number(yr), amount: Number(amt) || 0, vestingYears: 1 };
        }).filter(r => r.year > 0);
      continue;
    }
    // Housing override: convert empty/0 → null wrapper
    if (path === "housingOverride.monthlyHousingCost") {
      if (v == null || v === 0 || isNaN(v)) o.housingOverride = null;
      else o.housingOverride = { monthlyHousingCost: Number(v) };
      continue;
    }
    setNested(o, path, v);
  }
  return o;
}

function formFromOffer(form, offer) {
  for (const el of form.elements) {
    if (!el.name) continue;
    const path = el.name;
    if (path === "cash.baseYearly") {
      el.value = (offer.cash.baseYearly || []).join(", ");
      continue;
    }
    if (path === "cash.retention") {
      el.value = (offer.cash.retention || [])
        .map(r => `${r.year}:${r.amount}`).join(", ");
      continue;
    }
    if (path === "housingOverride.monthlyHousingCost") {
      el.value = offer.housingOverride?.monthlyHousingCost ?? "";
      continue;
    }
    const v = getNested(offer, path);
    if (el.type === "checkbox") el.checked = !!v;
    else if (v == null) el.value = "";
    else el.value = v;
  }
}

// ─── Editor wiring ──────────────────────────────────────────────────────────
let editingId = null;

function openEditor(offer) {
  editingId = offer.id;
  editorTitle.textContent = offer.meta.name ? `Edit: ${offer.meta.name}` : "New offer";
  // populate state-dependent dropdowns first
  fillLocationOptions(offer.meta.state);
  fillLocalityOptions(offer.meta.state);
  formFromOffer(editorForm, offer);
  // set selects after options exist
  stateSel.value = offer.meta.state || "TX";
  locSel.value = offer.meta.locationKey || "";
  localitySel.value = offer.meta.localityKey || "";
  if (typeof editor.showModal === "function") editor.showModal();
  else editor.setAttribute("open", "");
}

function closeEditor() {
  editingId = null;
  if (typeof editor.close === "function") editor.close();
  else editor.removeAttribute("open");
}

$("#btn-add-offer").addEventListener("click", () => {
  const o = DEFAULT_OFFER();
  state.offers.push(o);
  openEditor(o);
});

$("#editor-close").addEventListener("click", () => {
  // If user closes without saving, drop newly-added empty offer
  if (editingId) {
    const o = state.offers.find(x => x.id === editingId);
    if (o && o.meta.name === "New offer" && !o._touched) {
      state.offers = state.offers.filter(x => x.id !== editingId);
    }
  }
  closeEditor();
  render();
});

$("#editor-cancel").addEventListener("click", () => $("#editor-close").click());

editorForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const idx = state.offers.findIndex(x => x.id === editingId);
  if (idx < 0) return;
  const updated = offerFromForm(editorForm, state.offers[idx]);
  updated.id = state.offers[idx].id;
  updated._touched = true;
  state.offers[idx] = updated;
  persist();
  closeEditor();
  render();
});

// ─── Top bar actions ────────────────────────────────────────────────────────
$("#btn-export").addEventListener("click", () => exportJSON(state));
$("#input-import").addEventListener("change", async (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  try {
    const data = await importJSON(f);
    if (data?.offers) {
      state = data;
      persist();
      render();
    } else {
      alert("Invalid file: missing 'offers' field.");
    }
  } catch (err) {
    alert("Failed to import: " + err.message);
  }
  e.target.value = "";
});
$("#btn-share").addEventListener("click", async () => {
  const url = location.origin + location.pathname + encodeStateToHash(state);
  try {
    await navigator.clipboard.writeText(url);
    alert("Share URL copied to clipboard.\n\nNote: this URL contains your offer details. Treat as sensitive.");
  } catch {
    prompt("Copy this URL (sensitive — contains offer details):", url);
  }
});
$("#btn-clear").addEventListener("click", () => {
  if (confirm("Delete all offers and reset settings?")) {
    state = JSON.parse(JSON.stringify(initialState));
    clearAll();
    render();
  }
});

// Global settings inputs
const gFiling = $("#g-filing");
const gDiscount = $("#g-discount");
const gYears = $("#g-years");
gFiling.value = state.settings.filingStatus;
gDiscount.value = state.settings.discountRate;
gYears.value = state.settings.horizonYears;
gFiling.addEventListener("change", () => { state.settings.filingStatus = gFiling.value; persist(); render(); });
gDiscount.addEventListener("change", () => { state.settings.discountRate = Number(gDiscount.value) || 0; persist(); render(); });
gYears.addEventListener("change", () => { state.settings.horizonYears = Number(gYears.value) || 5; persist(); render(); });

// ─── Rendering ──────────────────────────────────────────────────────────────
function summaryFor(offer) {
  // Apply global horizon if offer's contractYears wasn't user-set; we keep
  // the offer's own contractYears as authoritative since it's per-offer.
  return summarize(offer, federalData, stateTaxData, localTaxData, beaData, {
    discountRate: state.settings.discountRate
  });
}

function locationLabel(offer) {
  const stName = stateTaxData.states[offer.meta.state]?.name || offer.meta.state || "";
  const m = beaData.metros[offer.meta.locationKey];
  if (m) return `${m.name}, ${stName}`;
  return stName;
}

function renderOffers() {
  if (state.offers.length === 0) {
    offersList.innerHTML = `
      <div class="empty">
        No offers yet. Click <strong>+ Add offer</strong> to enter the first one.
      </div>`;
    return;
  }

  offersList.innerHTML = state.offers.map(o => {
    const s = summaryFor(o);
    return `
      <article class="offer-card" data-id="${o.id}">
        <h3>${escapeHtml(o.meta.name || "(unnamed)")}</h3>
        <div class="loc">${escapeHtml(locationLabel(o))} · ${o.meta.contractYears || 0}y</div>
        <div class="headline">${fmtUSD(s.totals.colAdjustedTotal, { compact: true })}</div>
        <div class="sub">${o.meta.contractYears}-yr COL-adjusted total economic value</div>
        <div class="sub">After-tax cash: ${fmtUSD(s.totals.afterTaxCash, { compact: true })} · NPV: ${fmtUSD(s.npv.colAdjustedTotal, { compact: true })}</div>
        <div class="sub">Effective hourly: ${s.effectiveHourly != null ? fmtUSD(s.effectiveHourly, { fractionDigits: 0 }) : "—"}/hr · RPP: ${fmtNumber(s.effRpp, 1)}</div>
        <div class="actions">
          <button data-act="edit">Edit</button>
          <button data-act="duplicate">Duplicate</button>
          <button data-act="delete" class="danger">Delete</button>
        </div>
      </article>
    `;
  }).join("");

  offersList.querySelectorAll(".offer-card").forEach(card => {
    const id = card.dataset.id;
    card.querySelector('[data-act="edit"]').addEventListener("click", () => {
      const o = state.offers.find(x => x.id === id);
      if (o) openEditor(o);
    });
    card.querySelector('[data-act="duplicate"]').addEventListener("click", () => {
      const o = state.offers.find(x => x.id === id);
      if (o) {
        const copy = JSON.parse(JSON.stringify(o));
        copy.id = "o_" + Math.random().toString(36).slice(2);
        copy.meta.name = (o.meta.name || "Offer") + " (copy)";
        state.offers.push(copy);
        persist();
        render();
      }
    });
    card.querySelector('[data-act="delete"]').addEventListener("click", () => {
      if (confirm("Delete this offer?")) {
        state.offers = state.offers.filter(x => x.id !== id);
        persist();
        render();
      }
    });
  });
}

function renderComparison() {
  if (state.offers.length === 0) {
    comparison.innerHTML = "";
    return;
  }
  const summaries = state.offers.map(o => ({ o, s: summaryFor(o) }));
  const headers = summaries.map(({ o }) => `<th>${escapeHtml(o.meta.name || "(unnamed)")}</th>`).join("");

  const bestIdx = (vals, dir = "max") => {
    let bi = 0, bv = vals[0];
    vals.forEach((v, i) => {
      if (dir === "max" ? v > bv : v < bv) { bi = i; bv = v; }
    });
    return bi;
  };

  const rowComputed = (label, vals, fmt = fmtUSD, dir = "max", extraCls = "") => {
    const bi = bestIdx(vals, dir);
    const cells = vals.map((v, i) =>
      `<td class="${i === bi ? "best-cell" : ""}">${fmt(v)}</td>`
    ).join("");
    return `<tr class="${extraCls}"><td>${label}</td>${cells}</tr>`;
  };

  // Headline rows
  const colTotals = summaries.map(x => x.s.totals.colAdjustedTotal);
  const afterTax  = summaries.map(x => x.s.totals.afterTaxCash);
  const totalEcon = summaries.map(x => x.s.totals.totalEconomicValue);
  const npvTotal  = summaries.map(x => x.s.npv.colAdjustedTotal);
  const npvAfter  = summaries.map(x => x.s.npv.afterTaxCash);
  const effHrly   = summaries.map(x => x.s.effectiveHourly || 0);
  const grossW2   = summaries.map(x => x.s.totals.grossW2);
  const taxes     = summaries.map(x => x.s.totals.tax);
  const benefits  = summaries.map(x => x.s.totals.benefitsValue);
  const colCash   = summaries.map(x => x.s.totals.colAdjustedCash);
  const rpps      = summaries.map(x => x.s.effRpp);

  // Year-by-year rows: show only up to the global horizon (or each offer's contractYears)
  const horizon = state.settings.horizonYears;
  const yearRows = [];
  const maxYears = Math.max(...summaries.map(x => x.s.schedule.length));
  for (let y = 1; y <= Math.min(maxYears, horizon); y++) {
    const cells = summaries.map(({ s }) => {
      const r = s.schedule[y - 1];
      return r ? `<td>${fmtUSD(r.afterTaxCash, { compact: true })}</td>` : `<td>—</td>`;
    }).join("");
    yearRows.push(`<tr><td>Year ${y} after-tax</td>${cells}</tr>`);
  }
  for (let y = 1; y <= Math.min(maxYears, horizon); y++) {
    const cells = summaries.map(({ s }) => {
      const r = s.schedule[y - 1];
      return r ? `<td>${fmtUSD(r.colAdjustedCash, { compact: true })}</td>` : `<td>—</td>`;
    }).join("");
    yearRows.push(`<tr><td>Year ${y} COL-adj cash</td>${cells}</tr>`);
  }

  // Component breakdown bars (totals across contract): cash/benefits/taxes
  const breakdownRows = summaries.map(({ s }) => {
    const total = s.totals.grossW2 + s.totals.benefitsValue;
    const w = (n) => total > 0 ? `${(100 * n / total).toFixed(1)}%` : "0%";
    return `
      <td>
        <div class="bar-row">
          <span style="width:${w(s.totals.afterTaxCash)};background:var(--accent-2)" title="After-tax cash"></span>
          <span style="width:${w(s.totals.tax)};background:var(--warn)" title="Taxes"></span>
          <span style="width:${w(s.totals.benefitsValue)};background:var(--accent)" title="Benefits"></span>
        </div>
      </td>
    `;
  }).join("");

  comparison.innerHTML = `
    <h2>Comparison</h2>
    <div class="compare-table-wrap">
    <table class="compare">
      <thead><tr><th></th>${headers}</tr></thead>
      <tbody>
        <tr class="section"><td colspan="${1 + summaries.length}">Headline (contract total)</td></tr>
        ${rowComputed("COL-adj total economic value", colTotals, (v) => fmtUSD(v, { compact: true }), "max", "headline")}
        ${rowComputed("After-tax cash", afterTax, (v) => fmtUSD(v, { compact: true }))}
        ${rowComputed("Total economic value (cash + benefits)", totalEcon, (v) => fmtUSD(v, { compact: true }))}
        ${rowComputed("NPV — COL-adj total", npvTotal, (v) => fmtUSD(v, { compact: true }))}
        ${rowComputed("NPV — after-tax cash", npvAfter, (v) => fmtUSD(v, { compact: true }))}
        ${rowComputed("Effective $/hour (after-tax)", effHrly, (v) => fmtUSD(v, { fractionDigits: 0 }))}

        <tr class="section"><td colspan="${1 + summaries.length}">Components (contract total)</td></tr>
        <tr><td>Gross W-2 wages</td>${grossW2.map(v => `<td>${fmtUSD(v, { compact: true })}</td>`).join("")}</tr>
        <tr><td>Total taxes (fed+state+local+FICA)</td>${taxes.map(v => `<td>${fmtUSD(v, { compact: true })}</td>`).join("")}</tr>
        <tr><td>Benefits value</td>${benefits.map(v => `<td>${fmtUSD(v, { compact: true })}</td>`).join("")}</tr>
        <tr><td>COL-adj after-tax cash only</td>${colCash.map(v => `<td>${fmtUSD(v, { compact: true })}</td>`).join("")}</tr>
        <tr><td>Effective RPP applied</td>${rpps.map(v => `<td>${fmtNumber(v, 1)}</td>`).join("")}</tr>
        <tr><td>Cash · Tax · Benefits split</td>${breakdownRows}</tr>

        <tr class="section"><td colspan="${1 + summaries.length}">Year by year</td></tr>
        ${yearRows.join("")}
      </tbody>
    </table>
    </div>
    <div class="legend">
      <span><i style="background:var(--accent-2)"></i>After-tax cash</span>
      <span><i style="background:var(--warn)"></i>Taxes</span>
      <span><i style="background:var(--accent)"></i>Benefits</span>
    </div>
  `;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function render() {
  renderOffers();
  renderComparison();
}

render();
