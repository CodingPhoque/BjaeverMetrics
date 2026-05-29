// theme.jsx — design tokens (3 visual directions), jersey presets, helpers, seeded season.
// Exported to window at the bottom.

// ---- Themes -------------------------------------------------------------
// Each theme is a flat token set written to CSS custom properties on the app root.
// The team (jersey) colors are SEPARATE and user-chosen — themes only style the chrome.
const THEMES = {
  studio: {
    label: "Studio",
    blurb: "Lyst, redaktionelt, masser af luft",
    fontDisplay: "'Hanken Grotesk', system-ui, sans-serif",
    fontBody: "'Hanken Grotesk', system-ui, sans-serif",
    fontMono: "'JetBrains Mono', monospace",
    vars: {
      "--bg": "oklch(0.985 0.004 95)",
      "--surface": "oklch(1 0 0)",
      "--surface-2": "oklch(0.972 0.005 95)",
      "--surface-inset": "oklch(0.955 0.006 95)",
      "--text": "oklch(0.24 0.012 80)",
      "--text-dim": "oklch(0.52 0.012 80)",
      "--text-faint": "oklch(0.66 0.01 80)",
      "--border": "oklch(0.905 0.006 95)",
      "--border-strong": "oklch(0.84 0.008 95)",
      "--accent": "oklch(0.58 0.12 158)",
      "--accent-text": "oklch(0.99 0.01 158)",
      "--accent-soft": "oklch(0.94 0.04 158)",
      "--radius": "12px",
      "--radius-sm": "8px",
      "--radius-lg": "18px",
      "--shadow": "0 1px 2px oklch(0.4 0.02 80 / 0.04), 0 8px 24px oklch(0.4 0.02 80 / 0.06)",
      "--shadow-sm": "0 1px 2px oklch(0.4 0.02 80 / 0.06)",
      "--track": "oklch(0.93 0.006 95)",
    },
  },
  broadcast: {
    label: "Broadcast",
    blurb: "Mørkt dashboard, høj kontrast, sportsgrafik",
    fontDisplay: "'Space Grotesk', system-ui, sans-serif",
    fontBody: "'Hanken Grotesk', system-ui, sans-serif",
    fontMono: "'JetBrains Mono', monospace",
    vars: {
      "--bg": "oklch(0.17 0.014 264)",
      "--surface": "oklch(0.215 0.016 264)",
      "--surface-2": "oklch(0.255 0.018 264)",
      "--surface-inset": "oklch(0.2 0.016 264)",
      "--text": "oklch(0.97 0.004 264)",
      "--text-dim": "oklch(0.72 0.012 264)",
      "--text-faint": "oklch(0.55 0.014 264)",
      "--border": "oklch(0.32 0.018 264)",
      "--border-strong": "oklch(0.42 0.02 264)",
      "--accent": "oklch(0.86 0.19 128)",
      "--accent-text": "oklch(0.2 0.05 128)",
      "--accent-soft": "oklch(0.32 0.06 128)",
      "--radius": "8px",
      "--radius-sm": "5px",
      "--radius-lg": "12px",
      "--shadow": "0 2px 8px oklch(0 0 0 / 0.3), 0 16px 40px oklch(0 0 0 / 0.35)",
      "--shadow-sm": "0 1px 3px oklch(0 0 0 / 0.3)",
      "--track": "oklch(0.28 0.016 264)",
    },
  },
  klub: {
    label: "Klub",
    blurb: "Varmt papir, klubnært, blødt",
    fontDisplay: "'Bricolage Grotesque', system-ui, sans-serif",
    fontBody: "'Hanken Grotesk', system-ui, sans-serif",
    fontMono: "'JetBrains Mono', monospace",
    vars: {
      "--bg": "oklch(0.955 0.018 75)",
      "--surface": "oklch(0.99 0.01 80)",
      "--surface-2": "oklch(0.93 0.022 75)",
      "--surface-inset": "oklch(0.915 0.024 75)",
      "--text": "oklch(0.26 0.022 55)",
      "--text-dim": "oklch(0.5 0.022 55)",
      "--text-faint": "oklch(0.64 0.02 55)",
      "--border": "oklch(0.88 0.022 75)",
      "--border-strong": "oklch(0.8 0.026 70)",
      "--accent": "oklch(0.56 0.15 38)",
      "--accent-text": "oklch(0.99 0.01 38)",
      "--accent-soft": "oklch(0.92 0.05 50)",
      "--radius": "16px",
      "--radius-sm": "10px",
      "--radius-lg": "22px",
      "--shadow": "0 1px 2px oklch(0.4 0.04 55 / 0.06), 0 10px 30px oklch(0.4 0.04 55 / 0.09)",
      "--shadow-sm": "0 1px 2px oklch(0.4 0.04 55 / 0.08)",
      "--track": "oklch(0.91 0.022 75)",
    },
  },
};

const DENSITY = {
  luftig: { "--pad": "32px", "--gap": "24px", "--unit": "1" },
  kompakt: { "--pad": "20px", "--gap": "16px", "--unit": "0.85" },
};

function applyTheme(el, themeKey, density) {
  if (!el) return;
  const theme = THEMES[themeKey] || THEMES.studio;
  Object.entries(theme.vars).forEach(([k, v]) => el.style.setProperty(k, v));
  Object.entries(DENSITY[density] || DENSITY.luftig).forEach(([k, v]) => el.style.setProperty(k, v));
  el.style.setProperty("--font-display", theme.fontDisplay);
  el.style.setProperty("--font-body", theme.fontBody);
  el.style.setProperty("--font-mono", theme.fontMono);
}

// ---- Jersey color presets ----------------------------------------------
// Common football kit colors — used as swatches; user can also pick a free color.
const JERSEY_PRESETS = [
  { name: "Rød", hex: "#d62839" },
  { name: "Blå", hex: "#1d6fe0" },
  { name: "Hvid", hex: "#f4f4f5" },
  { name: "Sort", hex: "#1c1c1e" },
  { name: "Gul", hex: "#f4c020" },
  { name: "Grøn", hex: "#1f9d54" },
  { name: "Navy", hex: "#1b2a52" },
  { name: "Himmelblå", hex: "#4aa8e0" },
  { name: "Orange", hex: "#ef7a1a" },
  { name: "Bordeaux", hex: "#7a1f33" },
  { name: "Lilla", hex: "#6c3fb5" },
  { name: "Pink", hex: "#e85a9a" },
];

// Pick readable text color for a given jersey hex
function readableOn(hex) {
  const h = (hex || "#000").replace("#", "");
  if (h.length < 6) return "#fff";
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.62 ? "#1c1c1e" : "#ffffff";
}

// ---- Time helpers -------------------------------------------------------
function fmtClock(sec) {
  if (sec == null || isNaN(sec)) return "–:––";
  sec = Math.max(0, Math.round(sec));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function fmtDateDa(iso) {
  if (!iso) return "";
  const months = ["jan.", "feb.", "mar.", "apr.", "maj", "jun.", "jul.", "aug.", "sep.", "okt.", "nov.", "dec."];
  const [y, m, d] = iso.split("-").map(Number);
  return `${d}. ${months[m - 1]} ${y}`;
}

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ---- Seeded season ------------------------------------------------------
// Realistic-looking history for IF Frem Bjæverskov so the season view has substance.
// Home team is always Frem; possession/passes are "our" numbers vs the opponent.
const HOME_TEAM = "IF Frem Bjæverskov";
function seedSeason() {
  const raw = [
    { date: "2026-03-01", opp: "Ringsted IF", venue: "Bjæverskov Stadion", poss: 48, p1: 45, p2: 51, passes: 176, oppPasses: 198 },
    { date: "2026-03-15", opp: "Køge BK 2", venue: "Køge Idrætspark", poss: 51, p1: 49, p2: 53, passes: 189, oppPasses: 181 },
    { date: "2026-03-29", opp: "Herfølge BK", venue: "Bjæverskov Stadion", poss: 47, p1: 52, p2: 42, passes: 168, oppPasses: 205 },
    { date: "2026-04-12", opp: "Greve Fodbold", venue: "Greve Stadion", poss: 53, p1: 50, p2: 56, passes: 201, oppPasses: 174 },
    { date: "2026-04-26", opp: "Tune IF", venue: "Bjæverskov Stadion", poss: 55, p1: 58, p2: 52, passes: 213, oppPasses: 166 },
    { date: "2026-05-10", opp: "Solrød FC", venue: "Solrød Idrætscenter", poss: 58, p1: 61, p2: 55, passes: 224, oppPasses: 158 },
    { date: "2026-05-24", opp: "Vallensbæk IF", venue: "Bjæverskov Stadion", poss: 56, p1: 54, p2: 59, passes: 218, oppPasses: 169 },
  ];
  return raw.map((r, i) => ({
    id: `seed-${i}`,
    date: r.date,
    homeTeam: HOME_TEAM,
    awayTeam: r.opp,
    venue: r.venue,
    homeColor: "#d62839",
    awayColor: "#1d6fe0",
    seed: true,
    stats: {
      possession: { home: r.poss, away: 100 - r.poss, h1: { home: r.p1, away: 100 - r.p1 }, h2: { home: r.p2, away: 100 - r.p2 } },
      passes: {
        home: r.passes, away: r.oppPasses,
        h1: { home: Math.round(r.passes * 0.52), away: Math.round(r.oppPasses * 0.5) },
        h2: { home: r.passes - Math.round(r.passes * 0.52), away: r.oppPasses - Math.round(r.oppPasses * 0.5) },
      },
    },
  }));
}

Object.assign(window, {
  THEMES, DENSITY, applyTheme, JERSEY_PRESETS, readableOn,
  fmtClock, fmtDateDa, todayISO, seedSeason, HOME_TEAM,
});
