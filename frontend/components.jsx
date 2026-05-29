// components.jsx — shared UI primitives + functional icons. Exported to window.
const { useState, useRef, useEffect } = React;

// ---- Icons (simple functional UI glyphs, stroked) ----------------------
function Icon({ name, size = 20, stroke = 2, style }) {
  const p = { fill: "none", stroke: "currentColor", strokeWidth: stroke, strokeLinecap: "round", strokeLinejoin: "round" };
  const paths = {
    upload: <><path {...p} d="M12 16V4M7 9l5-5 5 5" /><path {...p} d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></>,
    video: <><rect {...p} x="3" y="5" width="18" height="14" rx="2" /><path {...p} d="M10 9l5 3-5 3z" /></>,
    calendar: <><rect {...p} x="3" y="5" width="18" height="16" rx="2" /><path {...p} d="M3 9h18M8 3v4M16 3v4" /></>,
    play: <path {...p} d="M7 5l12 7-12 7z" />,
    pause: <><path {...p} d="M8 5v14M16 5v14" /></>,
    check: <path {...p} d="M4 12l5 5L20 6" />,
    chevronRight: <path {...p} d="M9 6l6 6-6 6" />,
    chevronLeft: <path {...p} d="M15 6l-6 6 6 6" />,
    chart: <><path {...p} d="M4 20V4M4 20h16" /><path {...p} d="M8 16v-3M12 16V8M16 16v-6M20 16v-9" /></>,
    list: <><path {...p} d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" /></>,
    pin: <><path {...p} d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11z" /><circle {...p} cx="12" cy="10" r="2.5" /></>,
    whistle: <><circle {...p} cx="9" cy="14" r="5" /><path {...p} d="M14 12h7l-2 4h-5M9 9V5h3" /></>,
    arrowUp: <path {...p} d="M12 19V5M6 11l6-6 6 6" />,
    arrowDown: <path {...p} d="M12 5v14M6 13l6 6 6-6" />,
    plus: <path {...p} d="M12 5v14M5 12h14" />,
    flag: <><path {...p} d="M5 21V4M5 4h13l-3 4 3 4H5" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" style={style}>{paths[name]}</svg>;
}

// ---- Logo placeholder ---------------------------------------------------
function Logo({ size = 34 }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{
        width: size, height: size, borderRadius: 9, background: "var(--accent)", color: "var(--accent-text)",
        display: "grid", placeItems: "center", fontFamily: "var(--font-display)", fontWeight: 700,
        fontSize: size * 0.5, letterSpacing: "-0.03em", boxShadow: "var(--shadow-sm)",
      }}>BM</div>
      <div style={{ lineHeight: 1.05 }}>
        <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 16, letterSpacing: "-0.01em" }}>BjæverMetrics</div>
        <div style={{ fontSize: 11, color: "var(--text-faint)", letterSpacing: "0.04em", textTransform: "uppercase" }}>IF Frem Bjæverskov</div>
      </div>
    </div>
  );
}

// ---- Button -------------------------------------------------------------
function Button({ children, onClick, variant = "primary", disabled, size = "md", icon, iconRight, style, full }) {
  const [hov, setHov] = useState(false);
  const sizes = { md: { padding: "11px 18px", fontSize: 15 }, lg: { padding: "15px 26px", fontSize: 16 }, sm: { padding: "8px 13px", fontSize: 13.5 } };
  const variants = {
    primary: { background: disabled ? "var(--surface-2)" : "var(--accent)", color: disabled ? "var(--text-faint)" : "var(--accent-text)", border: "1px solid transparent" },
    ghost: { background: hov ? "var(--surface-2)" : "transparent", color: "var(--text)", border: "1px solid var(--border)" },
    subtle: { background: hov ? "var(--surface-inset)" : "var(--surface-2)", color: "var(--text)", border: "1px solid transparent" },
  };
  return (
    <button onClick={disabled ? undefined : onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        ...sizes[size], ...variants[variant], display: "inline-flex", alignItems: "center", justifyContent: "center",
        gap: 9, borderRadius: "var(--radius-sm)", fontFamily: "var(--font-body)", fontWeight: 600, cursor: disabled ? "not-allowed" : "pointer",
        transition: "filter .15s, background .15s, transform .1s", width: full ? "100%" : "auto",
        filter: hov && !disabled && variant === "primary" ? "brightness(1.06)" : "none", letterSpacing: "-0.005em", ...style,
      }}>
      {icon && <Icon name={icon} size={size === "lg" ? 19 : 17} />}
      {children}
      {iconRight && <Icon name={iconRight} size={size === "lg" ? 19 : 17} />}
    </button>
  );
}

// ---- Card ---------------------------------------------------------------
function Card({ children, style, pad = true, label, hint }) {
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", boxShadow: "var(--shadow-sm)", ...style }}>
      {label && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: "18px 22px 0" }}>
          <h3 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 15, fontWeight: 700, letterSpacing: "-0.01em" }}>{label}</h3>
          {hint && <span style={{ fontSize: 12, color: "var(--text-faint)" }}>{hint}</span>}
        </div>
      )}
      <div style={{ padding: pad ? "22px" : 0 }}>{children}</div>
    </div>
  );
}

// ---- Form field ---------------------------------------------------------
function Field({ label, optional, children, hint }) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-dim)", letterSpacing: "0.01em" }}>{label}</span>
        {optional && <span style={{ fontSize: 11.5, color: "var(--text-faint)", fontWeight: 500 }}>valgfri</span>}
      </div>
      {children}
      {hint && <div style={{ fontSize: 12, color: "var(--text-faint)", marginTop: 6 }}>{hint}</div>}
    </label>
  );
}

const inputStyle = {
  width: "100%", boxSizing: "border-box", padding: "12px 14px", borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-strong)", background: "var(--surface)", color: "var(--text)",
  fontFamily: "var(--font-body)", fontSize: 15, outline: "none", transition: "border-color .15s, box-shadow .15s",
};
function TextInput({ value, onChange, placeholder, type = "text", style }) {
  const [foc, setFoc] = useState(false);
  return (
    <input type={type} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)}
      onFocus={() => setFoc(true)} onBlur={() => setFoc(false)}
      style={{ ...inputStyle, borderColor: foc ? "var(--accent)" : "var(--border-strong)", boxShadow: foc ? "0 0 0 3px var(--accent-soft)" : "none", ...style }} />
  );
}

// ---- Jersey color picker (swatches + free picker) ----------------------
function JerseyPicker({ value, onChange }) {
  const customRef = useRef(null);
  const isPreset = JERSEY_PRESETS.some((p) => p.hex.toLowerCase() === (value || "").toLowerCase());
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8 }}>
        {JERSEY_PRESETS.map((p) => {
          const active = p.hex.toLowerCase() === (value || "").toLowerCase();
          return (
            <button key={p.hex} title={p.name} onClick={() => onChange(p.hex)}
              style={{
                aspectRatio: "1", borderRadius: "var(--radius-sm)", background: p.hex, cursor: "pointer",
                border: active ? "2.5px solid var(--accent)" : "1px solid var(--border-strong)",
                boxShadow: active ? "0 0 0 3px var(--accent-soft)" : "none",
                display: "grid", placeItems: "center", transition: "transform .1s, box-shadow .15s",
              }}>
              {active && <Icon name="check" size={16} stroke={3} style={{ color: readableOn(p.hex) }} />}
            </button>
          );
        })}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10 }}>
        <button onClick={() => customRef.current && customRef.current.click()}
          style={{
            display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 12px", borderRadius: "var(--radius-sm)",
            border: !isPreset && value ? "2px solid var(--accent)" : "1px dashed var(--border-strong)",
            background: "var(--surface-2)", color: "var(--text-dim)", cursor: "pointer", fontSize: 13, fontWeight: 600,
            fontFamily: "var(--font-body)",
          }}>
          <span style={{ width: 18, height: 18, borderRadius: 5, background: value || "transparent", border: "1px solid var(--border-strong)" }} />
          Egen farve
        </button>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-faint)", textTransform: "uppercase" }}>{value || "—"}</span>
        <input ref={customRef} type="color" value={value || "#888888"} onChange={(e) => onChange(e.target.value)}
          style={{ position: "absolute", width: 0, height: 0, opacity: 0, pointerEvents: "none" }} />
      </div>
    </div>
  );
}

// ---- Possession split bar ----------------------------------------------
function SplitBar({ home, away, homeColor, awayColor, height = 14, showLabels = false }) {
  return (
    <div>
      <div style={{ display: "flex", height, borderRadius: 999, overflow: "hidden", background: "var(--track)", boxShadow: "var(--shadow-sm) inset" }}>
        <div style={{ width: `${home}%`, background: homeColor, transition: "width .6s cubic-bezier(.2,.7,.2,1)" }} />
        <div style={{ width: `${away}%`, background: awayColor, transition: "width .6s cubic-bezier(.2,.7,.2,1)" }} />
      </div>
      {showLabels && (
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--text-dim)" }}>
          <span>{home}%</span><span>{away}%</span>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { Icon, Logo, Button, Card, Field, TextInput, JerseyPicker, SplitBar, inputStyle });
