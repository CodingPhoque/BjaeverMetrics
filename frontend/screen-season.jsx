// screen-season.jsx — season overview: trend chart + KPIs + match table. Exported to window.
const { useState: useStateS, useMemo } = React;

// --- line/area trend chart ----------------------------------------------
function TrendChart({ data, metric, accent, height = 220 }) {
  const [hover, setHover] = useStateS(null);
  const W = 760, H = height, padL = 38, padR = 16, padT = 18, padB = 34;
  const vals = data.map((d) => metric === "possession" ? d.poss : d.passes);
  const isPct = metric === "possession";
  const minV = isPct ? Math.max(0, Math.min(...vals) - 8) : Math.min(...vals) - 20;
  const maxV = isPct ? Math.min(100, Math.max(...vals) + 8) : Math.max(...vals) + 20;
  const x = (i) => padL + (i / Math.max(1, data.length - 1)) * (W - padL - padR);
  const y = (v) => padT + (1 - (v - minV) / (maxV - minV)) * (H - padT - padB);
  const linePath = data.map((d, i) => `${i ? "L" : "M"}${x(i)},${y(vals[i])}`).join(" ");
  const areaPath = `${linePath} L${x(data.length - 1)},${H - padB} L${x(0)},${H - padB} Z`;
  const gridLines = isPct ? [25, 50, 75] : null;

  return (
    <div style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }}
        onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id="bm-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity="0.22" />
            <stop offset="100%" stopColor={accent} stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* 50% reference for possession */}
        {isPct && (
          <g>
            <line x1={padL} x2={W - padR} y1={y(50)} y2={y(50)} stroke="var(--border-strong)" strokeWidth="1" strokeDasharray="4 4" />
            <text x={W - padR} y={y(50) - 5} textAnchor="end" fontSize="10" fill="var(--text-faint)" fontFamily="var(--font-mono)">50%</text>
          </g>
        )}
        {gridLines && gridLines.filter((g) => g !== 50).map((g) => (
          <line key={g} x1={padL} x2={W - padR} y1={y(g)} y2={y(g)} stroke="var(--border)" strokeWidth="1" />
        ))}
        <path d={areaPath} fill="url(#bm-area)" />
        <path d={linePath} fill="none" stroke={accent} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        {data.map((d, i) => (
          <g key={i} onMouseEnter={() => setHover(i)} style={{ cursor: "pointer" }}>
            <rect x={x(i) - (W / data.length) / 2} y={padT} width={W / data.length} height={H - padT - padB} fill="transparent" />
            <circle cx={x(i)} cy={y(vals[i])} r={hover === i ? 6 : 4} fill="var(--surface)" stroke={accent} strokeWidth="2.5" />
            <text x={x(i)} y={H - padB + 16} textAnchor="middle" fontSize="10" fill="var(--text-faint)" fontFamily="var(--font-mono)">{d.short}</text>
          </g>
        ))}
      </svg>
      {hover != null && (
        <div style={{
          position: "absolute", left: `${(x(hover) / W) * 100}%`, top: 0, transform: "translateX(-50%)",
          background: "var(--text)", color: "var(--bg)", padding: "7px 11px", borderRadius: 8, fontSize: 12, pointerEvents: "none", whiteSpace: "nowrap", boxShadow: "var(--shadow)",
        }}>
          <div style={{ fontWeight: 700 }}>{data[hover].opp}</div>
          <div style={{ fontFamily: "var(--font-mono)", opacity: 0.85 }}>{isPct ? `${vals[hover]}% besiddelse` : `${vals[hover]} afl.`}</div>
        </div>
      )}
    </div>
  );
}

function Sparkline({ data, metric, accent }) {
  const vals = data.map((d) => metric === "possession" ? d.poss : d.passes);
  const W = 120, H = 36, min = Math.min(...vals), max = Math.max(...vals);
  const x = (i) => (i / (vals.length - 1)) * W;
  const y = (v) => H - ((v - min) / Math.max(1, max - min)) * (H - 6) - 3;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H}>
      <path d={vals.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ")} fill="none" stroke={accent} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={x(vals.length - 1)} cy={y(vals[vals.length - 1])} r="3" fill={accent} />
    </svg>
  );
}

function KpiCard({ label, value, unit, delta, deltaLabel }) {
  const up = delta > 0, flat = delta === 0;
  const col = flat ? "var(--text-faint)" : up ? "oklch(0.6 0.15 150)" : "oklch(0.6 0.17 25)";
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "18px 20px", boxShadow: "var(--shadow-sm)" }}>
      <div style={{ fontSize: 12.5, color: "var(--text-dim)", fontWeight: 600 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginTop: 8 }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em" }}>{value}</span>
        <span style={{ fontSize: 15, color: "var(--text-faint)", fontWeight: 600 }}>{unit}</span>
      </div>
      {delta != null && (
        <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 8, fontSize: 12.5, color: col, fontWeight: 600, whiteSpace: "nowrap" }}>
          {!flat && <Icon name={up ? "arrowUp" : "arrowDown"} size={14} stroke={2.5} />}
          <span>{flat ? "uændret" : `${up ? "+" : ""}${delta}${unit === "%" ? " pp" : ""}`}</span>
          <span style={{ color: "var(--text-faint)", fontWeight: 500 }}>{deltaLabel}</span>
        </div>
      )}
    </div>
  );
}

function SeasonScreen({ matches, onNew, onOpen, layout = "kombineret" }) {
  const [metric, setMetric] = useStateS("possession");
  // perspective = the club (home team's numbers)
  const series = useMemo(() => matches.map((m) => {
    const months = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];
    const [, mo, da] = m.date.split("-").map(Number);
    return { id: m.id, opp: m.awayTeam, short: `${da}/${mo}`, poss: m.stats.possession.home, passes: m.stats.passes.home, date: m.date, raw: m };
  }), [matches]);

  if (series.length === 0) {
    return (
      <div style={{ maxWidth: 1060, margin: "0 auto", padding: "0 28px 80px" }}>
        <header style={{ padding: "40px 0 26px", display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--accent)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>Sæson 2026</div>
            <h1 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em" }}>Sæsonoversigt</h1>
            <p style={{ color: "var(--text-dim)", fontSize: 15, marginTop: 8 }}>Ingen kampe er gemt endnu.</p>
          </div>
          <Button icon="plus" onClick={onNew}>Analyser ny kamp</Button>
        </header>
        <Card>
          <div style={{ display: "grid", placeItems: "center", minHeight: 220, textAlign: "center" }}>
            <div>
              <div style={{ width: 48, height: 48, borderRadius: 12, background: "var(--accent-soft)", color: "var(--accent)", display: "grid", placeItems: "center", margin: "0 auto 14px" }}>
                <Icon name="video" size={24} />
              </div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: 18, fontWeight: 700 }}>Start med første analyse</div>
              <div style={{ color: "var(--text-dim)", fontSize: 14, marginTop: 6 }}>Upload en kampvideo for at bygge sæsonen op.</div>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  const avgPoss = Math.round(series.reduce((a, b) => a + b.poss, 0) / series.length);
  const avgPass = Math.round(series.reduce((a, b) => a + b.passes, 0) / series.length);
  const last = series[series.length - 1], prev = series[series.length - 2];
  const possDelta = prev ? last.poss - prev.poss : 0;
  const passDelta = prev ? last.passes - prev.passes : 0;
  const accent = "var(--accent)";

  const MetricToggle = () => (
    <div style={{ display: "inline-flex", background: "var(--surface-2)", borderRadius: "var(--radius-sm)", padding: 3, border: "1px solid var(--border)" }}>
      {[["possession", "Boldbesiddelse"], ["passes", "Afleveringer"]].map(([k, l]) => (
        <button key={k} onClick={() => setMetric(k)} style={{
          padding: "7px 14px", borderRadius: "calc(var(--radius-sm) - 2px)", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, fontFamily: "var(--font-body)",
          background: metric === k ? "var(--surface)" : "transparent", color: metric === k ? "var(--text)" : "var(--text-dim)", boxShadow: metric === k ? "var(--shadow-sm)" : "none",
        }}>{l}</button>
      ))}
    </div>
  );

  const chartCard = (big) => (
    <Card>
      <div style={{ marginBottom: 18 }}>
        <h3 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 16, fontWeight: 700 }}>Udvikling over sæsonen</h3>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap", marginTop: 6 }}>
          <p style={{ margin: 0, fontSize: 13, color: "var(--text-dim)" }}>{HOME_TEAM} · {series.length} kampe</p>
          <MetricToggle />
        </div>
      </div>
      <TrendChart data={series} metric={metric} accent={accent} height={big ? 280 : 210} />
    </Card>
  );

  const tableCard = () => (
    <Card label="Alle kampe" hint={`${series.length} kampe`} pad={false}>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--text-faint)", fontSize: 11.5, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              <th style={thS}>Dato</th><th style={thS}>Modstander</th><th style={{ ...thS, textAlign: "right" }}>Besiddelse</th><th style={{ ...thS, textAlign: "right" }}>Afl.</th><th style={thS}></th>
            </tr>
          </thead>
          <tbody>
            {[...series].reverse().map((s) => (
              <tr key={s.id} onClick={() => onOpen(s.raw)} style={{ borderTop: "1px solid var(--border)", cursor: "pointer" }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--surface-2)"} onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
                <td style={{ ...tdS, fontFamily: "var(--font-mono)", color: "var(--text-dim)", whiteSpace: "nowrap" }}>{fmtDateDa(s.date)}</td>
                <td style={{ ...tdS, fontWeight: 600 }}>{s.opp}</td>
                <td style={{ ...tdS, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                  <span style={{ color: s.poss >= 50 ? "var(--text)" : "var(--text-dim)", fontWeight: 600 }}>{s.poss}%</span>
                </td>
                <td style={{ ...tdS, textAlign: "right", fontFamily: "var(--font-mono)" }}>{s.passes}</td>
                <td style={{ ...tdS, textAlign: "right", color: "var(--text-faint)" }}><Icon name="chevronRight" size={16} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );

  const kpis = (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
      <KpiCard label="Gns. boldbesiddelse" value={avgPoss} unit="%" delta={possDelta} deltaLabel="vs. sidste kamp" />
      <KpiCard label="Gns. afleveringer" value={avgPass} unit="" delta={passDelta} deltaLabel="vs. sidste kamp" />
      <KpiCard label="Seneste besiddelse" value={last.poss} unit="%" delta={last.poss - avgPoss} deltaLabel="vs. sæsonsnit" />
    </div>
  );

  return (
    <div style={{ maxWidth: 1060, margin: "0 auto", padding: "0 28px 80px" }}>
      <header style={{ padding: "40px 0 26px", display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
        <div>
          <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--accent)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>Sæson 2026</div>
          <h1 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em" }}>Sæsonoversigt</h1>
          <p style={{ color: "var(--text-dim)", fontSize: 15, marginTop: 8 }}>Følg {HOME_TEAM}s udvikling kamp for kamp.</p>
        </div>
        <Button icon="plus" onClick={onNew}>Analysér ny kamp</Button>
      </header>

      {layout === "tabel" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
            {kpis}
          </div>
          {tableCard()}
        </div>
      ) : layout === "graf" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {chartCard(true)}
          {kpis}
          {tableCard()}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {kpis}
          <div style={{ display: "grid", gridTemplateColumns: "1.55fr 1fr", gap: 20, alignItems: "start" }}>
            {chartCard(false)}
            {tableCard()}
          </div>
        </div>
      )}
    </div>
  );
}

const thS = { padding: "14px 22px", fontWeight: 600 };
const tdS = { padding: "13px 22px" };

Object.assign(window, { SeasonScreen });
