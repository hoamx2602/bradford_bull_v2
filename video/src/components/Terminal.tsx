import React from "react";
import { C, inter } from "../theme";

/** macOS-style window chrome bar with traffic lights + an optional caption.
 *  (Kept as a clean "app window" frame — no terminal/command styling.) */
export const WindowChrome: React.FC<{ title?: string }> = ({ title }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "0 18px",
      height: 44,
      background: "rgba(255,255,255,0.05)",
      borderBottom: `1px solid ${C.cardLine}`,
    }}
  >
    {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
      <div key={c} style={{ width: 13, height: 13, borderRadius: "50%", background: c }} />
    ))}
    {title ? (
      <div style={{ marginLeft: 14, fontFamily: inter, fontWeight: 500, fontSize: 19, color: C.muted }}>
        {title}
      </div>
    ) : null}
  </div>
);
