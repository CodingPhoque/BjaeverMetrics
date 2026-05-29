# BjæverMetrics — Frontend

Webinterface til upload, halvlegs-markering og visning af kampstatistik for
IF Frem Bjæverskov. Bygget som en selvstændig React-prototype (ingen build-step
nødvendig) der i dag kører på **mock-data**. Alle backend-kald er samlet ét sted
(`api.js`), så I kun skal røre én fil for at koble på den rigtige pipeline.

---

## Kør den

Det er ren statiske filer — server mappen og åbn `index.html`:

```bash
# enten
python -m http.server -d frontend 5500
# eller fra jeres Flask/FastAPI-app: server frontend/ som static files
```

> React, ReactDOM og Babel hentes fra CDN, og JSX transformeres i browseren.
> Det er fint til prototype/intern brug. Skal det i rigtig produktion, så
> precompile JSX (f.eks. Vite) — men funktionalitet og layout er uændret.

---

## Filstruktur

| Fil | Ansvar |
|-----|--------|
| `index.html` | Indgang. Loader fonts, React/Babel og alle scripts i rækkefølge. |
| `api.js` | **Datalaget / backend-sømmen.** Mock i dag — her kobler I på. |
| `app.jsx` | Rod-komponent: skærm-navigation (sæson → upload → analyse → kamp), tweaks. |
| `theme.jsx` | Designtokens (3 temaer), trøjefarve-presets, hjælpefunktioner, seed-sæson. |
| `screen-upload.jsx` | Upload + holdopsætning + interaktiv video-trim (halvleg-markering). |
| `screen-processing.jsx` | "Analyserer video"-tilstand (spejler pipeline-trinene). |
| `screen-stats.jsx` | Enkeltkamp: boldbesiddelse + afleveringer. |
| `screen-season.jsx` | Sæsonoversigt: trendgraf, KPI'er, kamptabel. |
| `tweaks-panel.jsx` | Internt panel til at skifte tema/layout. Kan fjernes i produktion (se nederst). |

---

## Sådan kobler I backend på — `api.js`

Frontenden kalder **kun** disse tre funktioner:

```js
BMApi.loadSeason()        // -> Match[]      henter hele sæsonen
BMApi.analyzeMatch(draft) // -> { stats }    kører pipeline på den uploadede video
BMApi.saveMatch(matches)  // -> void         persisterer
```

I dag er de mock (genererede tal + `localStorage`). Erstat indmaden med jeres
HTTP-kald — formen ind/ud er beskrevet herunder.

### `analyzeMatch(draft)` — input matcher `build_io_artifact()`

`draft` indeholder præcis de felter jeres `src/fodbold/io/metadata.py` allerede
forventer:

| draft-felt | → `build_io_artifact` argument |
|-----------|-------------------------------|
| `draft.videoFile` (+ selve fil-blob) | `video_path` |
| `draft.date` (`YYYY-MM-DD`) | `date` |
| `draft.homeTeam` / `draft.awayTeam` | `home_team` / `away_team` |
| `draft.venue` (kan være tom) | `venue` |
| `draft.segments.h1s` / `h1e` | `half1_start_seconds` / `half1_end_seconds` |
| `draft.segments.h2s` / `h2e` | `half2_start_seconds` / `half2_end_seconds` |

> Trim-UI'et håndhæver allerede samme regel som `_validate_match_segments`:
> `0 ≤ h1s < h1e ≤ h2s < h2e ≤ varighed`. Halvlegspausen (mellem `h1e` og `h2s`)
> klippes fra.

Produktionsflow: gør `analyzeMatch` `async`, POST video + io-felter til pipelinen,
poll til `stats_artifact` er klar, returnér `artifact.stats` på Match-formen.
Husk så at `await` den i `app.jsx → finishProcessing`.

### Match-formen ↔ jeres database

Frontendens Match-objekt mapper 1:1 til `matches` + `match_stats` og til
`stats_artifact.example.json`:

```js
{
  id, date, homeTeam, awayTeam, venue,   // matches-tabellen
  homeColor, awayColor,                  // NY — se note nedenfor
  stats: {
    possession: { home, away,            // match_stats: metric_name="possession", segment="total"
                  h1: {home,away},        //              segment_name="first_half"
                  h2: {home,away} },      //              segment_name="second_half"
    passes:     { home, away, h1:{…}, h2:{…} }  // metric_name="passes"
  }
}
```

`home`/`away` = `home_value`/`away_value`. Boldbesiddelse er i procent, afleveringer
i antal — som i jeres `unit`-felt.

---

## ⚠️ Skema-note: trøjefarver

Trøjefarverne (`homeColor` / `awayColor`) bruges både til at adskille holdene i
K-means **og** som holdidentitet i hele statistikvisningen, men de findes ikke i
`schema.sql` endnu. Tilføj dem til `matches`, f.eks.:

```sql
ALTER TABLE matches ADD COLUMN home_color TEXT;
ALTER TABLE matches ADD COLUMN away_color TEXT;
```

og send dem med ind i io-artifactet, så pipelinen kan matche K-means-klyngerne mod
de farver brugeren har valgt.

---

## Fjern tweaks-panelet i produktion

Panelet er kun til at sammenligne designretninger. For at fjerne det:

1. Slet `<TweaksPanel>…</TweaksPanel>`-blokken nederst i `app.jsx`.
2. Slet `<script ... src="tweaks-panel.jsx">` i `index.html` og selve filen.
3. Erstat `const [t, setTweak] = useTweaks(TWEAK_DEFAULTS)` med en fast konstant,
   f.eks. `const t = { theme: "studio", density: "luftig", seasonLayout: "graf", matchColors: "hold" }`.

Det valgte standarddesign er **Studio-tema**, **graf-layout** på sæsonoversigten
og **holdfarver** på enkeltkampe.
