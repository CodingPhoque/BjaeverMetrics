// screen-stats.jsx — single match result: possession + passes. Exported to window.

function Donut({ home, away, homeColor, awayColor, size = 188 }) {
  const r = size / 2 - 16, c = 2 * Math.PI * r;
  const homeLen = c * (home / 100);
  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={awayColor} strokeWidth="22" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={homeColor} strokeWidth="22"
          strokeDasharray={`${homeLen} ${c - homeLen}`} style={{ transition: "stroke-dasharray .7s cubic-bezier(.2,.7,.2,1)" }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
        <div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 38, fontWeight: 700, letterSpacing: "-0.02em", color: homeColor === "#f4f4f5" ? "var(--text)" : homeColor }}>{home}%</div>
          <div style={{ fontSize: 11.5, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>besiddelse</div>
        </div>
      </div>
    </div>
  );
}

function HalfRow({ label, home, away, homeColor, awayColor }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, color: "var(--text-dim)", fontWeight: 600, marginBottom: 6 }}>
        <span style={{ fontFamily: "var(--font-mono)", color: "var(--text)" }}>{home}%</span>
        <span>{label}</span>
        <span style={{ fontFamily: "var(--font-mono)", color: "var(--text)" }}>{away}%</span>
      </div>
      <SplitBar home={home} away={away} homeColor={homeColor} awayColor={awayColor} height={10} />
    </div>
  );
}

function PassBars({ stats, homeColor, awayColor }) {
  const max = Math.max(stats.home, stats.away, 1);
  const row = (lbl, hv, av) => {
    const hmax = Math.max(hv, av, 1);
    return (
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 12, color: "var(--text-faint)", fontWeight: 600, marginBottom: 7, textTransform: "uppercase", letterSpacing: "0.05em" }}>{lbl}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 7 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 600, width: 42, textAlign: "right" }}>{hv}</span>
          <div style={{ flex: 1, height: 12, background: "var(--track)", borderRadius: 999, overflow: "hidden" }}>
            <div style={{ width: `${(hv / hmax) * 100}%`, height: "100%", background: homeColor, transition: "width .6s" }} />
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 600, width: 42, textAlign: "right" }}>{av}</span>
          <div style={{ flex: 1, height: 12, background: "var(--track)", borderRadius: 999, overflow: "hidden" }}>
            <div style={{ width: `${(av / hmax) * 100}%`, height: "100%", background: awayColor, transition: "width .6s" }} />
          </div>
        </div>
      </div>
    );
  };
  return (
    <div>
      <div style={{ display: "flex", gap: 24, marginBottom: 22 }}>
        <BigStat value={stats.home} color={homeColor} label="Hjemme" />
        <div style={{ width: 1, background: "var(--border)" }} />
        <BigStat value={stats.away} color={awayColor} label="Ude" />
      </div>
      <div style={{ borderTop: "1px solid var(--border)", paddingTop: 18 }}>
        {row("1. halvleg", stats.h1.home, stats.h1.away)}
        {row("2. halvleg", stats.h2.home, stats.h2.away)}
      </div>
    </div>
  );
}

function BigStat({ value, color, label }) {
  return (
    <div style={{ flex: 1 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={{ width: 11, height: 11, borderRadius: 4, background: color, border: "1px solid var(--border-strong)" }} />
        <span style={{ fontSize: 12.5, color: "var(--text-dim)", fontWeight: 600 }}>{label}</span>
      </div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 40, fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 12, color: "var(--text-faint)", marginTop: 4 }}>afleveringer</div>
    </div>
  );
}

function MatchStatsScreen({ match, onSeason, isNew, colorMode = "hold" }) {
  const { stats, homeTeam, awayTeam } = match;
  // Two color designs: team jersey colors, or the neutral theme palette (like the season chart).
  const homeColor = colorMode === "standard" ? "var(--accent)" : match.homeColor;
  const awayColor = colorMode === "standard" ? "var(--text-dim)" : match.awayColor;
  const winner = stats.possession.home === stats.possession.away ? null : stats.possession.home > stats.possession.away ? "home" : "away";
  return (
    <div style={{ maxWidth: 1060, margin: "0 auto", padding: "0 28px 80px" }}>
      {isNew && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, background: "var(--accent-soft)", color: "var(--text)", borderRadius: "var(--radius-sm)", padding: "11px 16px", margin: "28px 0 0", fontSize: 14, fontWeight: 600 }}>
          <Icon name="check" size={17} style={{ color: "var(--accent)" }} /> Analyse færdig — kampen er gemt i sæsonen.
        </div>
      )}
      {/* header */}
      <header style={{ padding: "32px 0 26px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 18 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 8 }}>
            <TeamHead color={homeColor} name={homeTeam} />
            <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-faint)", fontSize: 14 }}>vs</span>
            <TeamHead color={awayColor} name={awayTeam} />
          </div>
          <div style={{ display: "flex", gap: 16, color: "var(--text-dim)", fontSize: 13.5 }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><Icon name="calendar" size={15} /> {fmtDateDa(match.date)}</span>
            {match.venue && <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><Icon name="pin" size={15} /> {match.venue}</span>}
          </div>
        </div>
        <Button variant="ghost" iconRight="chart" onClick={onSeason}>Se sæsonen</Button>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* possession */}
        <Card label="Boldbesiddelse" hint="hele kampen">
          <div style={{ display: "flex", gap: 26, alignItems: "center" }}>
            <Donut home={stats.possession.home} away={stats.possession.away} homeColor={homeColor} awayColor={awayColor} />
            <div style={{ flex: 1 }}>
              <Legend color={homeColor} name={homeTeam} value={`${stats.possession.home}%`} lead={winner === "home"} />
              <div style={{ height: 12 }} />
              <Legend color={awayColor} name={awayTeam} value={`${stats.possession.away}%`} lead={winner === "away"} />
            </div>
          </div>
          <div style={{ borderTop: "1px solid var(--border)", marginTop: 22, paddingTop: 20 }}>
            <HalfRow label="1. halvleg" home={stats.possession.h1.home} away={stats.possession.h1.away} homeColor={homeColor} awayColor={awayColor} />
            <HalfRow label="2. halvleg" home={stats.possession.h2.home} away={stats.possession.h2.away} homeColor={homeColor} awayColor={awayColor} />
          </div>
        </Card>

        {/* passes */}
        <Card label="Afleveringer" hint="antal pr. hold">
          <PassBars stats={stats.passes} homeColor={homeColor} awayColor={awayColor} />
        </Card>
      </div>
    </div>
  );
}

function TeamHead({ color, name }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
      <span style={{ width: 18, height: 22, borderRadius: "4px 4px 5px 5px", background: color, border: "1px solid var(--border-strong)" }} />
      <span style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em" }}>{name}</span>
    </div>
  );
}

function Legend({ color, name, value, lead }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 9, minWidth: 0 }}>
        <span style={{ width: 13, height: 13, borderRadius: 4, background: color, border: "1px solid var(--border-strong)", flexShrink: 0 }} />
        <span style={{ fontSize: 14.5, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name}</span>
        {lead && <span style={{ fontSize: 10.5, fontWeight: 700, color: "var(--accent)", background: "var(--accent-soft)", padding: "2px 7px", borderRadius: 999, textTransform: "uppercase", letterSpacing: "0.04em", flexShrink: 0, whiteSpace: "nowrap" }}>Mest bold</span>}
      </div>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700 }}>{value}</span>
    </div>
  );
}

Object.assign(window, { MatchStatsScreen });
