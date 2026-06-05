// app.jsx - root: state machine, navigation, tweaks wiring.
const { useState: useStateA, useEffect: useEffectA, useRef: useRefA } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "studio",
  "density": "luftig",
  "seasonLayout": "graf",
  "matchColors": "hold"
}/*EDITMODE-END*/;

function emptyDraft() {
  return {
    videoFile: null, videoBlob: null, videoUrl: null, duration: 0,
    segments: { h1s: 0, h1e: 0, h2s: 0, h2e: 0 },
    homeTeam: "IF Frem Bjaeverskov", awayTeam: "",
    homeColor: "#d62839", awayColor: "#1d6fe0",
    date: todayISO(), venue: "",
    goalsHome: 0, goalsAway: 0,
    shotsOnTargetHome: 0, shotsOnTargetAway: 0,
  };
}

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const rootRef = useRefA(null);
  const [screen, setScreen] = useStateA("season");
  const [draft, setDraft] = useStateA(emptyDraft);
  const [matches, setMatches] = useStateA([]);
  const [current, setCurrent] = useStateA(null);
  const [isNew, setIsNew] = useStateA(false);

  useEffectA(() => { applyTheme(rootRef.current, t.theme, t.density); }, [t.theme, t.density]);
  useEffectA(() => {
    BMApi.loadSeason()
      .then(setMatches)
      .catch((error) => {
        console.error(error);
        setMatches([]);
      });
  }, []);

  const startUpload = () => { setDraft(emptyDraft()); setScreen("upload"); };

  const submitDraft = async (d) => {
    setDraft(d);
    setScreen("processing");
    try {
      const { match } = await BMApi.analyzeMatch(d);
      const freshMatches = await BMApi.loadSeason();
      setMatches(freshMatches);
      setCurrent(match);
      setIsNew(true);
      setScreen("match");
    } catch (error) {
      alert(error.message || "Analysen fejlede.");
      setScreen("upload");
    }
  };

  const openMatch = (m) => { setCurrent(m); setIsNew(false); setScreen("match"); };

  return (
    <div ref={rootRef} style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)", fontFamily: "var(--font-body)" }}>
      <TopBar screen={screen} onSeason={() => setScreen("season")} onUpload={startUpload} />
      <main>
        {screen === "upload" && <UploadScreen draft={draft} setDraft={setDraft} onSubmit={submitDraft} />}
        {screen === "processing" && <ProcessingScreen draft={draft} />}
        {screen === "match" && current && <MatchStatsScreen match={current} isNew={isNew} colorMode={t.matchColors} onSeason={() => setScreen("season")} />}
        {screen === "season" && <SeasonScreen matches={matches} layout={t.seasonLayout} onNew={startUpload} onOpen={openMatch} />}
      </main>

      <TweaksPanel>
        <TweakSection label="Visuel retning" />
        <TweakRadio label="Tema" value={t.theme}
          options={[{ value: "studio", label: "Studio" }, { value: "broadcast", label: "Broadcast" }, { value: "klub", label: "Klub" }]}
          onChange={(v) => setTweak("theme", v)} />
        <div style={{ fontSize: 12, color: "var(--text-dim, #888)", margin: "-4px 2px 8px", lineHeight: 1.4 }}>{THEMES[t.theme].blurb}</div>
        <TweakRadio label="Densitet" value={t.density}
          options={[{ value: "luftig", label: "Luftig" }, { value: "kompakt", label: "Kompakt" }]}
          onChange={(v) => setTweak("density", v)} />
        <TweakSection label="Sæsonoversigt" />
        <TweakRadio label="Layout" value={t.seasonLayout}
          options={[{ value: "kombineret", label: "Kombineret" }, { value: "graf", label: "Graf" }, { value: "tabel", label: "Tabel" }]}
          onChange={(v) => setTweak("seasonLayout", v)} />
        <TweakSection label="Kampvisning" />
        <TweakRadio label="Farver" value={t.matchColors}
          options={[{ value: "hold", label: "Holdfarver" }, { value: "standard", label: "Standard" }]}
          onChange={(v) => setTweak("matchColors", v)} />
      </TweaksPanel>
    </div>
  );
}

function TopBar({ screen, onSeason, onUpload }) {
  const tab = (label, active, onClick) => (
    <button onClick={onClick} style={{
      padding: "8px 14px", borderRadius: "var(--radius-sm)", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, fontFamily: "var(--font-body)",
      background: active ? "var(--surface-2)" : "transparent", color: active ? "var(--text)" : "var(--text-dim)",
    }}>{label}</button>
  );
  return (
    <div style={{ position: "sticky", top: 0, zIndex: 20, background: "color-mix(in oklch, var(--bg) 86%, transparent)", backdropFilter: "blur(10px)", borderBottom: "1px solid var(--border)" }}>
      <div style={{ maxWidth: 1060, margin: "0 auto", padding: "14px 28px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Logo />
        <nav style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {tab("Sæson", screen === "season", onSeason)}
          {tab("Ny analyse", screen === "upload" || screen === "processing", onUpload)}
        </nav>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
