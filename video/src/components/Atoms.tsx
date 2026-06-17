import React from "react";
import { Img, staticFile } from "remotion";
import { C, mono, inter } from "../theme";
import { opt } from "../assets";

const initials = (name: string): string =>
  name
    .replace(/^.*·\s*/, "")
    .split(/\s+/)
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

/** Portrait: shows the photo if its file exists, else a mono-initial avatar.
 *  `ring` draws the brand accent ring (used for highlighted members). */
export const Avatar: React.FC<{
  name: string;
  file?: string;
  size?: number;
  ring?: boolean;
  radius?: number;
}> = ({ name, file, size = 230, ring, radius = 20 }) => {
  const src = file ? opt(file) : undefined;
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        overflow: "hidden",
        background: "linear-gradient(150deg, #14161D, #0A0B10)",
        border: `${ring ? 2.5 : 1.5}px solid ${ring ? C.red : C.cardLine}`,
        boxShadow: ring ? `0 0 32px rgba(255,59,48,0.35)` : "0 18px 40px rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
      }}
    >
      {src ? (
        <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      ) : (
        <span style={{ fontFamily: mono, fontWeight: 700, fontSize: size * 0.34, color: C.steel, letterSpacing: 1 }}>
          {initials(name)}
        </span>
      )}
    </div>
  );
};

/** A tile that shows a logo image if present, else a mono label. `light` gives
 *  it a white card so logos drawn for light backgrounds read clearly. */
export const LogoTile: React.FC<{
  file?: string;
  label: string;
  w: number;
  h: number;
  light?: boolean;
}> = ({ file, label, w, h, light }) => {
  const src = file ? opt(file) : undefined;
  const onLight = light && src;
  return (
    <div
      style={{
        width: w,
        height: h,
        borderRadius: 16,
        background: onLight ? "#FFFFFF" : C.card,
        border: `1px solid ${onLight ? "rgba(255,255,255,0.5)" : C.cardLine}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: src ? (onLight ? 22 : 24) : 12,
        boxShadow: onLight ? "0 10px 30px rgba(0,0,0,0.35)" : "none",
      }}
    >
      {src ? (
        <Img src={staticFile(src)} style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }} />
      ) : (
        <span style={{ fontFamily: mono, fontSize: 20, color: C.dim, textAlign: "center" }}>{label}</span>
      )}
    </div>
  );
};

/** Back-compat alias used by older code paths. */
export const LogoBox: React.FC<{ label: string; w: number; h: number }> = (p) => (
  <LogoTile {...p} />
);

export const PhotoCard: React.FC<{ name: string; file?: string }> = ({ name, file }) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
    <Avatar name={name} file={file} size={240} />
    <div style={{ fontFamily: inter, fontWeight: 600, fontSize: 26, color: C.white }}>{name}</div>
  </div>
);
