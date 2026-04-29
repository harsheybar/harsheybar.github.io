const KEY = "offer-compare/v1";

export function loadAll() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (e) {
    console.error("loadAll failed", e);
    return null;
  }
}

export function saveAll(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch (e) {
    console.error("saveAll failed", e);
  }
}

export function clearAll() {
  localStorage.removeItem(KEY);
}

export function exportJSON(state) {
  const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const stamp = new Date().toISOString().slice(0, 10);
  a.download = `offer-compare-${stamp}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function importJSON(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      try { resolve(JSON.parse(reader.result)); }
      catch (e) { reject(e); }
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

// URL hash share: base64(JSON). Uses encodeURIComponent to handle UTF-8 safely.
export function encodeStateToHash(state) {
  const json = JSON.stringify(state);
  const b64 = btoa(unescape(encodeURIComponent(json)));
  return `#s=${b64}`;
}

export function decodeStateFromHash(hash) {
  if (!hash || !hash.startsWith("#s=")) return null;
  try {
    const b64 = hash.slice(3);
    const json = decodeURIComponent(escape(atob(b64)));
    return JSON.parse(json);
  } catch (e) {
    console.warn("Failed to decode state from URL hash", e);
    return null;
  }
}
