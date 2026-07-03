// screen-processing.jsx — "analyserer video" state.
function ProcessingScreen({ draft }) {
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
          <div style={{ width: 92, height: 92, margin: "0 auto 22px" }}>
            <Spinner size={92} strokeWidth={3.2} showTrack />
          </div>
          <h1 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em" }}>Analyserer kampen</h1>
          <p style={{ color: "var(--text-dim)", fontSize: 14.5, marginTop: 8 }}>Dette kan tage lang tid. Du kan roligt lade fanen stå.</p>
        </div>

        <div style={{
          display: "flex", alignItems: "center", gap: 14, padding: "12px 16px", borderRadius: "var(--radius-sm)",
          background: "var(--surface)", border: "1px solid var(--border)", boxShadow: "var(--shadow-sm)",
        }}>
          <div style={{
            width: 26, height: 26, borderRadius: 999, flexShrink: 0, display: "grid", placeItems: "center",
            background: "var(--accent-soft)", color: "var(--accent)",
          }}>
            <Spinner />
          </div>
          <div style={{ fontSize: 14.5, fontWeight: 600, color: "var(--text)" }}>Video analyseres</div>
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

function Spinner({ size = 16, strokeWidth = 7, showTrack = false }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      role="status"
      aria-label="Video analyseres"
      style={{ display: "block", animation: "bm-spin 1s linear infinite" }}
    >
      {showTrack && <circle cx="24" cy="24" r="19" fill="none" stroke="var(--track)" strokeWidth={strokeWidth} />}
      <circle
        cx="24"
        cy="24"
        r="19"
        fill="none"
        stroke="var(--accent)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray="72 48"
      />
    </svg>
  );
}

Object.assign(window, { ProcessingScreen });
