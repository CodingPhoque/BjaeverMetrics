// screen-upload.jsx — upload + match setup + interactive video trim. Exported to window.
const { useState: useStateU, useRef: useRefU, useEffect: useEffectU, useCallback } = React;

// ---- Video trim timeline ------------------------------------------------
function TrimTimeline({ duration, segments, setSegments, videoRef, hasVideo, playhead, onSeek }) {
  const trackRef = useRefU(null);
  const [drag, setDrag] = useStateU(null); // handle key being dragged
  const MIN_GAP = Math.max(30, duration * 0.01);

  const pct = (t) => (duration ? (t / duration) * 100 : 0);
  const timeFromX = (clientX) => {
    const r = trackRef.current.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
    return ratio * duration;
  };

  const clampHandle = (key, t) => {
    const s = segments;
    if (key === "h1s") return Math.min(t, s.h1e - MIN_GAP);
    if (key === "h1e") return Math.min(Math.max(t, s.h1s + MIN_GAP), s.h2s);
    if (key === "h2s") return Math.min(Math.max(t, s.h1e), s.h2e - MIN_GAP);
    if (key === "h2e") return Math.max(t, s.h2s + MIN_GAP);
    return t;
  };

  useEffectU(() => {
    if (!drag) return;
    const move = (e) => {
      const t = clampHandle(drag, timeFromX(e.clientX));
      setSegments((s) => ({ ...s, [drag]: Math.max(0, Math.min(duration, t)) }));
      onSeek(t);
    };
    const up = () => setDrag(null);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
  }, [drag, segments, duration]);

  const handle = (key, label, color) => (
    <div onPointerDown={(e) => { e.preventDefault(); setDrag(key); }}
      style={{
        position: "absolute", left: `${pct(segments[key])}%`, top: -6, bottom: -6, transform: "translateX(-50%)",
        width: 18, cursor: "ew-resize", display: "flex", flexDirection: "column", alignItems: "center", zIndex: drag === key ? 5 : 3,
      }}>
      <div style={{
        width: 3, flex: 1, background: color, borderRadius: 2,
        boxShadow: drag === key ? "0 0 0 4px var(--accent-soft)" : "none",
      }} />
      <div style={{
        position: "absolute", top: -22, fontSize: 10.5, fontWeight: 700, fontFamily: "var(--font-mono)",
        background: color, color: readableOn(color), padding: "1px 5px", borderRadius: 4, whiteSpace: "nowrap",
      }}>{label}</div>
    </div>
  );

  const segBlock = (a, b, tone, txt) => (
    <div style={{
      position: "absolute", left: `${pct(a)}%`, width: `${pct(b) - pct(a)}%`, top: 0, bottom: 0,
      background: tone, display: "grid", placeItems: "center", overflow: "hidden",
    }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: "var(--accent-text)", letterSpacing: "0.02em", whiteSpace: "nowrap", opacity: 0.92 }}>{txt}</span>
    </div>
  );

  return (
    <div style={{ marginTop: 18 }}>
      {/* track */}
      <div ref={trackRef} style={{ position: "relative", height: 46, background: "var(--surface-inset)", borderRadius: "var(--radius-sm)", marginTop: 28, marginBottom: 10, userSelect: "none" }}
        onClick={(e) => { if (!drag) onSeek(timeFromX(e.clientX)); }}>
        {/* half-time gap hatch */}
        <div style={{
          position: "absolute", left: `${pct(segments.h1e)}%`, width: `${pct(segments.h2s) - pct(segments.h1e)}%`, top: 0, bottom: 0,
          backgroundImage: "repeating-linear-gradient(45deg, var(--track) 0 6px, transparent 6px 12px)", borderLeft: "1px dashed var(--border-strong)", borderRight: "1px dashed var(--border-strong)",
        }} />
        {segBlock(segments.h1s, segments.h1e, "var(--accent)", "1. HALVLEG")}
        {segBlock(segments.h2s, segments.h2e, "color-mix(in oklch, var(--accent) 78%, var(--text))", "2. HALVLEG")}
        {/* playhead */}
        <div style={{ position: "absolute", left: `${pct(playhead)}%`, top: -4, bottom: -4, width: 2, background: "var(--text)", transform: "translateX(-50%)", zIndex: 4, pointerEvents: "none", opacity: 0.7 }} />
        {handle("h1s", "1H ▸", "var(--accent)")}
        {handle("h1e", "◂ 1H", "var(--accent)")}
        {handle("h2s", "2H ▸", "color-mix(in oklch, var(--accent) 78%, var(--text))")}
        {handle("h2e", "◂ 2H", "color-mix(in oklch, var(--accent) 78%, var(--text))")}
      </div>
      {/* scale */}
      <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-faint)" }}>
        <span>0:00</span><span>{fmtClock(duration / 2)}</span><span>{fmtClock(duration)}</span>
      </div>

      {/* boundary editors */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginTop: 16 }}>
        {[
          ["h1s", "1. halvleg start"], ["h1e", "1. halvleg slut"],
          ["h2s", "2. halvleg start"], ["h2e", "2. halvleg slut"],
        ].map(([key, lbl]) => (
          <div key={key} style={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "10px 12px" }}>
            <div style={{ fontSize: 11.5, color: "var(--text-dim)", fontWeight: 600, marginBottom: 4 }}>{lbl}</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 19, fontWeight: 600, letterSpacing: "-0.01em" }}>{fmtClock(segments[key])}</div>
            <button onClick={() => setSegments((s) => ({ ...s, [key]: clampHandle(key, playhead) }))}
              style={{ marginTop: 6, fontSize: 11, fontWeight: 600, color: "var(--accent)", background: "none", border: "none", cursor: "pointer", padding: 0, fontFamily: "var(--font-body)" }}>
              Sæt til afspilning
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- Upload screen ------------------------------------------------------
function UploadScreen({ draft, setDraft, onSubmit }) {
  const videoRef = useRefU(null);
  const fileRef = useRefU(null);
  const [playing, setPlaying] = useStateU(false);
  const [playhead, setPlayhead] = useStateU(0);
  const [dragOver, setDragOver] = useStateU(false);

  const d = draft;
  const set = (patch) => setDraft((p) => ({ ...p, ...patch }));

  const loadFile = (file) => {
    if (!file || !file.type.startsWith("video")) return;
    if (d.videoUrl) URL.revokeObjectURL(d.videoUrl);
    const url = URL.createObjectURL(file);
    set({ videoFile: file.name, videoBlob: file, videoUrl: url });
  };

  const clearVideo = () => {
    if (d.videoUrl) URL.revokeObjectURL(d.videoUrl);
    if (fileRef.current) fileRef.current.value = "";
    setPlaying(false);
    setPlayhead(0);
    set({
      videoFile: null,
      videoBlob: null,
      videoUrl: null,
      duration: 0,
      segments: { h1s: 0, h1e: 0, h2s: 0, h2e: 0 },
    });
  };

  const onLoadedMeta = () => {
    const dur = videoRef.current.duration;
    if (!dur || !isFinite(dur)) return;
    // sensible default segments across the real video
    set({ duration: dur, segments: { h1s: dur * 0.02, h1e: dur * 0.46, h2s: dur * 0.54, h2e: dur * 0.99 } });
  };

  const seek = (t) => {
    setPlayhead(t);
    if (videoRef.current && d.videoUrl) { videoRef.current.currentTime = t; }
  };

  useEffectU(() => {
    const v = videoRef.current;
    if (!v) return;
    const onT = () => setPlayhead(v.currentTime);
    v.addEventListener("timeupdate", onT);
    return () => v.removeEventListener("timeupdate", onT);
  }, [d.videoUrl]);

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) { v.play(); setPlaying(true); } else { v.pause(); setPlaying(false); }
  };

  const useDemoTimeline = () => set({ videoFile: "demo-tidslinje", videoBlob: null, videoUrl: null, duration: 5700, segments: { h1s: 60, h1e: 2820, h2s: 3000, h2e: 5640 } });

  const valid = d.videoBlob && d.homeTeam && d.awayTeam && d.homeColor && d.awayColor && d.date && d.duration > 0 && d.homeColor !== d.awayColor;

  return (
    <div style={{ maxWidth: 1060, margin: "0 auto", padding: "0 28px 120px" }}>
      <header style={{ padding: "40px 0 8px" }}>
        <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--accent)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>Ny analyse</div>
        <h1 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 34, fontWeight: 700, letterSpacing: "-0.02em" }}>Forbered kamp til analyse</h1>
        <p style={{ color: "var(--text-dim)", fontSize: 15.5, maxWidth: 560, marginTop: 10, lineHeight: 1.5 }}>
          Upload kampvideoen, angiv holdene og deres trøjefarver, og markér hvornår hver halvleg starter og slutter. Så er klippet optimeret til at trække præcis statistik ud.
        </p>
      </header>

      {/* Step 1: video */}
      <section style={{ marginTop: 28 }}>
        <StepLabel n="1" title="Kampvideo" />
        {!d.videoFile ? (
          <div
            onClick={() => fileRef.current.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); loadFile(e.dataTransfer.files[0]); }}
            style={{
              border: `1.5px dashed ${dragOver ? "var(--accent)" : "var(--border-strong)"}`, borderRadius: "var(--radius-lg)",
              background: dragOver ? "var(--accent-soft)" : "var(--surface-2)", padding: "52px 24px", textAlign: "center", cursor: "pointer", transition: "all .15s",
            }}>
            <div style={{ width: 56, height: 56, borderRadius: 14, background: "var(--surface)", border: "1px solid var(--border)", display: "grid", placeItems: "center", margin: "0 auto 16px", color: "var(--accent)" }}>
              <Icon name="upload" size={26} />
            </div>
            <div style={{ fontSize: 17, fontWeight: 700, fontFamily: "var(--font-display)" }}>Slip kampvideoen her</div>
            <div style={{ color: "var(--text-dim)", fontSize: 14, marginTop: 6 }}>eller klik for at vælge en fil · MP4 fra Veo eller lignende</div>
            <input ref={fileRef} type="file" accept="video/*" style={{ display: "none" }} onChange={(e) => loadFile(e.target.files[0])} />
            <div style={{ marginTop: 18 }}>
              <button onClick={(e) => { e.stopPropagation(); useDemoTimeline(); }}
                style={{ fontSize: 13, fontWeight: 600, color: "var(--text-dim)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline", fontFamily: "var(--font-body)" }}>
                Eller prøv med en demo-tidslinje
              </button>
            </div>
          </div>
        ) : (
          <Card pad={false}>
            <div style={{ padding: 18 }}>
              {/* video preview */}
              <div style={{ position: "relative", borderRadius: "var(--radius-sm)", overflow: "hidden", background: "#000", aspectRatio: "16/9" }}>
                {d.videoUrl ? (
                  <video ref={videoRef} src={d.videoUrl} onLoadedMetadata={onLoadedMeta} onClick={togglePlay}
                    style={{ width: "100%", height: "100%", objectFit: "contain", display: "block", cursor: "pointer" }} />
                ) : (
                  <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center",
                    backgroundImage: "repeating-linear-gradient(45deg, #141414 0 14px, #1b1b1b 14px 28px)" }}>
                    <div style={{ textAlign: "center", color: "#9aa0a6" }}>
                      <Icon name="video" size={34} />
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, marginTop: 8 }}>demo-tidslinje · intet videopreview</div>
                    </div>
                  </div>
                )}
                {/* play control */}
                <button onClick={togglePlay} style={{
                  position: "absolute", left: 14, bottom: 14, width: 44, height: 44, borderRadius: 999, border: "none",
                  background: "rgba(0,0,0,0.55)", color: "#fff", display: "grid", placeItems: "center", cursor: "pointer", backdropFilter: "blur(4px)",
                }}>
                  <Icon name={playing && d.videoUrl ? "pause" : "play"} size={20} />
                </button>
                <div style={{ position: "absolute", right: 14, bottom: 16, fontFamily: "var(--font-mono)", fontSize: 13, color: "#fff", background: "rgba(0,0,0,0.5)", padding: "3px 9px", borderRadius: 6 }}>
                  {fmtClock(playhead)} / {fmtClock(d.duration)}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9, color: "var(--text-dim)", fontSize: 13.5 }}>
                  <Icon name="video" size={17} style={{ color: "var(--accent)" }} />
                  <span style={{ fontWeight: 600, color: "var(--text)" }}>{d.videoFile}</span>
                  <span>· {fmtClock(d.duration)}</span>
                </div>
                <Button variant="ghost" size="sm" icon="chevronLeft" onClick={clearVideo}>Fjern video</Button>
              </div>

              <div style={{ marginTop: 18, paddingTop: 18, borderTop: "1px solid var(--border)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <Icon name="whistle" size={17} style={{ color: "var(--accent)" }} />
                  <span style={{ fontWeight: 700, fontFamily: "var(--font-display)", fontSize: 15 }}>Markér halvlege</span>
                </div>
                <p style={{ margin: "0 0 4px", color: "var(--text-dim)", fontSize: 13.5, lineHeight: 1.5 }}>
                  Træk i håndtagene — eller scrub videoen til kickoff og tryk «Sæt til afspilning». Pausen imellem er halvlegspausen og udelades fra analysen.
                </p>
                <TrimTimeline duration={d.duration} segments={d.segments} setSegments={(fn) => set({ segments: typeof fn === "function" ? fn(d.segments) : fn })}
                  videoRef={videoRef} hasVideo={!!d.videoUrl} playhead={playhead} onSeek={seek} />
              </div>
            </div>
          </Card>
        )}
      </section>

      {/* Step 2: teams */}
      <section style={{ marginTop: 36 }}>
        <StepLabel n="2" title="Hold & trøjefarver" />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
          <TeamCard side="Hjemmehold" team={d.homeTeam} color={d.homeColor}
            onTeam={(v) => set({ homeTeam: v })} onColor={(v) => set({ homeColor: v })} />
          <TeamCard side="Udehold" team={d.awayTeam} color={d.awayColor}
            onTeam={(v) => set({ awayTeam: v })} onColor={(v) => set({ awayColor: v })} />
        </div>
        {d.homeColor && d.awayColor && d.homeColor === d.awayColor && (
          <div style={{ marginTop: 12, fontSize: 13, color: "oklch(0.55 0.18 25)", fontWeight: 600 }}>
            Holdene skal have forskellige trøjefarver, så systemet kan adskille dem.
          </div>
        )}
      </section>

      {/* Step 3: details */}
      <section style={{ marginTop: 36 }}>
        <StepLabel n="3" title="Kampdetaljer" />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
          <Card>
            <Field label="Kampdato">
              <div style={{ display: "flex", gap: 10 }}>
                <TextInput type="date" value={d.date} onChange={(v) => set({ date: v })} />
                <Button variant="ghost" onClick={() => set({ date: todayISO() })} icon="calendar" style={{ whiteSpace: "nowrap" }}>I dag</Button>
              </div>
            </Field>
          </Card>
          <Card>
            <Field label="Spillested" optional hint="F.eks. Bjæverskov Stadion">
              <TextInput value={d.venue} onChange={(v) => set({ venue: v })} placeholder="Spillested (venue)" />
            </Field>
          </Card>
        </div>
      </section>

      {/* Step 4: manual stats */}
      <section style={{ marginTop: 36 }}>
        <StepLabel n="4" title="Manuelle kampdata" />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
          <Card label="Mål" hint="bruges i stats-artifactet">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <Field label="Hjemme">
                <TextInput type="number" value={d.goalsHome} onChange={(v) => set({ goalsHome: Math.max(0, Number(v || 0)) })} />
              </Field>
              <Field label="Ude">
                <TextInput type="number" value={d.goalsAway} onChange={(v) => set({ goalsAway: Math.max(0, Number(v || 0)) })} />
              </Field>
            </div>
          </Card>
          <Card label="Skud på mål" hint="kan rettes manuelt">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <Field label="Hjemme">
                <TextInput type="number" value={d.shotsOnTargetHome} onChange={(v) => set({ shotsOnTargetHome: Math.max(0, Number(v || 0)) })} />
              </Field>
              <Field label="Ude">
                <TextInput type="number" value={d.shotsOnTargetAway} onChange={(v) => set({ shotsOnTargetAway: Math.max(0, Number(v || 0)) })} />
              </Field>
            </div>
          </Card>
        </div>
      </section>

      {/* sticky CTA */}
      <div style={{ position: "sticky", bottom: 0, marginTop: 36, padding: "16px 0", background: "linear-gradient(to top, var(--bg) 60%, transparent)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "14px 20px", boxShadow: "var(--shadow)" }}>
          <div style={{ fontSize: 13.5, color: "var(--text-dim)" }}>
            {valid ? <span style={{ display: "inline-flex", alignItems: "center", gap: 7, color: "var(--text)" }}><Icon name="check" size={16} style={{ color: "var(--accent)" }} /> Klar til analyse</span>
              : "Udfyld video, begge hold og trøjefarver for at fortsætte"}
          </div>
          <Button size="lg" disabled={!valid} iconRight="chevronRight" onClick={() => onSubmit(d)}>Analysér kamp</Button>
        </div>
      </div>
    </div>
  );
}

function StepLabel({ n, title }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
      <span style={{ width: 26, height: 26, borderRadius: 999, border: "1.5px solid var(--border-strong)", display: "grid", placeItems: "center", fontSize: 13, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-dim)" }}>{n}</span>
      <h2 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 19, fontWeight: 700, letterSpacing: "-0.01em" }}>{title}</h2>
    </div>
  );
}

function TeamCard({ side, team, color, onTeam, onColor }) {
  return (
    <Card>
      <div style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 16 }}>
        <div style={{ width: 34, height: 40, borderRadius: "6px 6px 7px 7px", background: color || "var(--surface-inset)", border: "1px solid var(--border-strong)", position: "relative", flexShrink: 0 }}>
          <div style={{ position: "absolute", top: -3, left: "50%", transform: "translateX(-50%)", width: 16, height: 6, borderRadius: "0 0 4px 4px", background: color || "var(--surface-inset)", border: "1px solid var(--border-strong)", borderTop: "none" }} />
        </div>
        <div>
          <div style={{ fontSize: 12, color: "var(--text-faint)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{side}</div>
          <div style={{ fontSize: 15.5, fontWeight: 700, fontFamily: "var(--font-display)" }}>{team || "Holdnavn"}</div>
        </div>
      </div>
      <Field label="Holdnavn"><TextInput value={team} onChange={onTeam} placeholder={side === "Hjemmehold" ? "f.eks. IF Frem Bjæverskov" : "f.eks. Ringsted IF"} /></Field>
      <div style={{ height: 16 }} />
      <Field label="Trøjefarve" hint="Bruges til at adskille holdene i analysen"><JerseyPicker value={color} onChange={onColor} /></Field>
    </Card>
  );
}

Object.assign(window, { UploadScreen });
