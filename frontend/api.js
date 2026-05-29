// api.js — DATA LAYER / BACKEND SEAM
// =============================================================================
// Alt der i dag er MOCK (genereret data + localStorage) ligger her, så I kun
// skal redigere ÉN fil for at koble på jeres rigtige backend.
//
// Frontenden kalder kun disse tre funktioner (se app.jsx):
//   BMApi.loadSeason()              -> Match[]            (henter sæsonen)
//   BMApi.analyzeMatch(draft)       -> { stats }          (kører pipeline på video)
//   BMApi.saveMatch(match)          -> void               (persisterer kampen)
//
// Match-formen frontenden forventer:
//   { id, date, homeTeam, awayTeam, venue, homeColor, awayColor,
//     stats: {
//       possession: { home, away, h1:{home,away}, h2:{home,away} },   // procent
//       passes:     { home, away, h1:{home,away}, h2:{home,away} },   // antal
//     } }
//
// Denne form mapper 1:1 til jeres database (matches + match_stats) og til
// stats_artifact.example.json — se README.md for det præcise mapping.
// =============================================================================

const LS_KEY = "bjaevermetrics_season_v1";

const BMApi = {
  // ---- Hent hele sæsonen --------------------------------------------------
  // MOCK: localStorage, ellers seed-data fra theme.jsx (seedSeason()).
  // PRODUKTION: GET /api/matches  → map matches + match_stats til Match-formen.
  loadSeason() {
    try {
      const s = localStorage.getItem(LS_KEY);
      if (s) return JSON.parse(s);
    } catch (e) {}
    return seedSeason();
  },

  // ---- Analysér en kamp ---------------------------------------------------
  // 'draft' indeholder præcis de felter build_io_artifact() skal bruge:
  //   { videoFile, duration, segments:{h1s,h1e,h2s,h2e},
  //     homeTeam, awayTeam, homeColor, awayColor, date, venue }
  //
  // MOCK: returnerer plausible tal med det samme.
  // PRODUKTION (asynkront flow):
  //   1) POST videoen + io_artifact (date, home_team, away_team, venue,
  //      half1_start_seconds … half2_end_seconds, fps_target) til pipelinen.
  //   2) Poll status indtil stats_artifact er klar.
  //   3) Returnér artifact.stats mappet til Match-formen herunder.
  //   Gør funktionen 'async' og 'await' den i app.jsx → finishProcessing().
  analyzeMatch(draft) {
    const homePoss = 46 + Math.round(Math.random() * 16);
    const h1 = Math.max(38, Math.min(64, homePoss + Math.round((Math.random() - 0.5) * 10)));
    const h2 = Math.max(38, Math.min(64, 2 * homePoss - h1));
    const homePass = 165 + Math.round(Math.random() * 70);
    const awayPass = Math.round((homePass * (100 - homePoss)) / homePoss + (Math.random() - 0.5) * 20);
    const split = (tot) => { const a = Math.round(tot * (0.48 + Math.random() * 0.08)); return { h1: a, h2: tot - a }; };
    const hp = split(homePass), ap = split(awayPass);
    return {
      stats: {
        possession: {
          home: homePoss, away: 100 - homePoss,
          h1: { home: h1, away: 100 - h1 }, h2: { home: h2, away: 100 - h2 },
        },
        passes: {
          home: homePass, away: awayPass,
          h1: { home: hp.h1, away: ap.h1 }, h2: { home: hp.h2, away: ap.h2 },
        },
      },
    };
  },

  // ---- Gem en kamp --------------------------------------------------------
  // MOCK: skriver hele sæsonen til localStorage.
  // PRODUKTION: håndteres typisk server-side i samme kald som analyseringen
  //   (db.save_stats_artifact). Behold blot en klient-cache her hvis ønsket.
  saveMatch(matches) {
    try { localStorage.setItem(LS_KEY, JSON.stringify(matches)); } catch (e) {}
  },

  resetSeason() {
    try { localStorage.removeItem(LS_KEY); } catch (e) {}
    return seedSeason();
  },
};

window.BMApi = BMApi;
