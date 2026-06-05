// api.js - data layer / local backend calls.
// Frontenden kalder kun funktionerne i BMApi.

const BMApi = {
  async loadSeason() {
    const response = await fetch("/api/matches");
    if (!response.ok) throw new Error("Kunne ikke hente sæsondata.");
    return response.json();
  },

  async analyzeMatch(draft) {
    if (!draft.videoBlob) throw new Error("Vælg en rigtig videofil forst.");

    const body = new FormData();
    body.append("video", draft.videoBlob);
    body.append("date", draft.date);
    body.append("home_team", draft.homeTeam);
    body.append("away_team", draft.awayTeam);
    body.append("home_color", draft.homeColor);
    body.append("away_color", draft.awayColor);
    body.append("venue", draft.venue || "");
    body.append("half1_start_seconds", draft.segments.h1s);
    body.append("half1_end_seconds", draft.segments.h1e);
    body.append("half2_start_seconds", draft.segments.h2s);
    body.append("half2_end_seconds", draft.segments.h2e);
    body.append("goals_home", draft.goalsHome || 0);
    body.append("goals_away", draft.goalsAway || 0);
    body.append("shots_on_target_home", draft.shotsOnTargetHome || 0);
    body.append("shots_on_target_away", draft.shotsOnTargetAway || 0);

    const response = await fetch("/api/analyze", { method: "POST", body });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Analysen fejlede.");
    }
    return payload;
  },

  //saveMatch() {},

  async resetSeason() {
    return this.loadSeason();
  },
};

window.BMApi = BMApi;
