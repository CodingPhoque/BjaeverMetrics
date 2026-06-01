// screen-processing.jsx — "analyserer video" state. Mirrors the real pipeline stages.
const { useState: useStateP, useEffect: useEffectP } = React;

function ProcessingScreen({ draft, onDone }) {
  const stages = [
    { key: "io", label: "Indlæser video & halvlegsmarkører", sub: "Klipper til 1. og 2. halvleg" },
    { key: "detect", label: "Detekterer spillere, bold og dommer", sub: "YOLO · billede for billede" },
    { key: "team", label: "Klassificerer hold ud fra trøjefarver", sub: "K-means matcher mod dine valgte farver" },
    { key: "track", label: "Sporer bevægelser over tid", sub: "ByteTrack tildeler ID til hver spiller" },
    { key: "poss", label: "Beregner boldbesiddelse", sub: "Pr. halvleg og samlet" },
    { key: "pass", label: "Tæller afleveringer", sub: "Pr. hold" },
    { key: "save", label: "Gemmer i sæsondatabasen", sub: "Klar til sammenligning" },
  ];
  const [active, setActive] = useStateP(0);
  const [progress, setProgress] = useStateP(0);

  useEffectP(() => {
    const total = 6400;
    const start = performance.now();
    let raf;
    const tick = (now) => {
      const p = Math.min(1, (now - start) / total);
      setProgress(p);
      setActive(Math.min(stages.length - 1, Math.floor(p * stages.length)));
      if (p < 1) raf = requestAnimationFrame(tick);
      else if (onDone) setTimeout(onDone, 550);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const homeC = draft.homeColor, awayC = draft.awayColor;

  return (
    <div style={{ minHeight: "100%", display: "grid", placeItems: "center", padding: "60px 28px" }}>
      <div style={{ width: "100%", maxWidth: 560 }}>
        {/* match chip */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 14, marginBottom: 30 }}>
          <TeamDot color={homeC} name={draft.homeTeam} />
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-faint)" }}>VS</span>
          <TeamDot color={awayC} name={draft.awayTeam} right />
        </div>

        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ position: "relative", width: 92, height: 92, margin: "0 auto 22px" }}>
            <svg width="92" height="92" viewBox="0 0 92 92" style={{ transform: "rotate(-90deg)" }}>
              <circle cx="46" cy="46" r="40" fill="none" stroke="var(--track)" strokeWidth="6" />
              <circle cx="46" cy="46" r="40" fill="none" stroke="var(--accent)" strokeWidth="6" strokeLinecap="round"
                strokeDasharray={2 * Math.PI * 40} strokeDashoffset={2 * Math.PI * 40 * (1 - progress)} style={{ transition: "stroke-dashoffset .2s linear" }} />
            </svg>
            <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", fontFamily: "var(--font-mono)", fontSize: 22, fontWeight: 600 }}>
              {Math.round(progress * 100)}<span style={{ fontSize: 13, color: "var(--text-faint)" }}>%</span>
            </div>
          </div>
          <h1 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em" }}>Analyserer kampen</h1>
          <p style={{ color: "var(--text-dim)", fontSize: 14.5, marginTop: 8 }}>Det tager normalt et par minutter pr. kamp. Du kan roligt lade fanen stå.</p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {stages.map((s, i) => {
            const done = i < active, current = i === active;
            return (
              <div key={s.key} style={{
                display: "flex", alignItems: "center", gap: 14, padding: "12px 16px", borderRadius: "var(--radius-sm)",
                background: current ? "var(--surface)" : "transparent", border: `1px solid ${current ? "var(--border)" : "transparent"}`,
                boxShadow: current ? "var(--shadow-sm)" : "none", opacity: i > active ? 0.45 : 1, transition: "all .3s",
              }}>
                <div style={{
                  width: 26, height: 26, borderRadius: 999, flexShrink: 0, display: "grid", placeItems: "center",
                  background: done ? "var(--accent)" : current ? "var(--accent-soft)" : "var(--surface-2)",
                  color: done ? "var(--accent-text)" : "var(--accent)", border: `1px solid ${done || current ? "transparent" : "var(--border)"}`,
                }}>
                  {done ? <Icon name="check" size={15} stroke={3} /> : current ? <Spinner /> : <span style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--text-faint)" }}>{i + 1}</span>}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14.5, fontWeight: 600, color: i > active ? "var(--text-dim)" : "var(--text)" }}>{s.label}</div>
                  {current && <div style={{ fontSize: 12.5, color: "var(--text-dim)", marginTop: 2 }}>{s.sub}</div>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function TeamDot({ color, name, right }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 9, flexDirection: right ? "row-reverse" : "row" }}>
      <span style={{ width: 16, height: 16, borderRadius: 5, background: color, border: "1px solid var(--border-strong)" }} />
      <span style={{ fontWeight: 700, fontSize: 15, fontFamily: "var(--font-display)" }}>{name}</span>
    </div>
  );
}

function Spinner() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" style={{ animation: "bm-spin 0.8s linear infinite" }}>
      <circle cx="8" cy="8" r="6" fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="28" strokeDashoffset="10" />
    </svg>
  );
}

Object.assign(window, { ProcessingScreen });
