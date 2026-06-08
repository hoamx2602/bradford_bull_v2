'use client'

import { useRef, useEffect, useState, useMemo } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { BodyZone } from '@/lib/types'
import { BODY_ZONES } from '@/lib/mock-data'

interface Props {
  zones?: BodyZone[]
}

// 23-zone body config — one distinct hue per region, flat vivid colour on 3D body.
// Convention: -l = viewer's LEFT (neg X in 3D), -r = viewer's RIGHT (pos X).
// Anchor (x,y,z) = world-space label point after model is scaled to TARGET_HEIGHT=3.6.
const ZONE_CONFIG: Record<string, { label: string; hue: number; x: number; y: number; z: number; front: boolean }> = {
  'head':          { label: 'Head',          hue: 270, x:  0.00, y: 3.30, z:  0.15, front: true  },
  'neck':          { label: 'Neck',          hue:  35, x:  0.00, y: 3.04, z:  0.14, front: true  },
  'shoulder-l':    { label: 'Shoulder L',    hue: 200, x: -0.32, y: 2.82, z:  0.05, front: true  },
  'shoulder-r':    { label: 'Shoulder R',    hue: 140, x:  0.32, y: 2.82, z:  0.05, front: true  },
  'chest-l':       { label: 'Chest L',       hue: 220, x: -0.12, y: 2.60, z:  0.22, front: true  },
  'chest-r':       { label: 'Chest R',       hue:   8, x:  0.12, y: 2.60, z:  0.22, front: true  },
  'abdomen-l':     { label: 'Abdomen L',     hue: 315, x: -0.12, y: 2.12, z:  0.20, front: true  },
  'abdomen-r':     { label: 'Abdomen R',     hue: 175, x:  0.12, y: 2.12, z:  0.20, front: true  },
  'upper-arm-l':   { label: 'Upper Arm L',   hue:  35, x: -0.50, y: 2.65, z:  0.00, front: true  },
  'upper-arm-r':   { label: 'Upper Arm R',   hue: 300, x:  0.50, y: 2.65, z:  0.00, front: true  },
  'forearm-l':     { label: 'Forearm L',     hue: 170, x: -0.65, y: 2.46, z:  0.00, front: true  },
  'forearm-r':     { label: 'Forearm R',     hue:  95, x:  0.65, y: 2.46, z:  0.00, front: true  },
  'hand-l':        { label: 'Hand L',        hue: 330, x: -0.78, y: 2.28, z:  0.00, front: true  },
  'hand-r':        { label: 'Hand R',        hue: 250, x:  0.78, y: 2.28, z:  0.00, front: true  },
  'spine':         { label: 'Spine',         hue:  50, x:  0.00, y: 2.60, z: -0.22, front: false },
  'back-l':        { label: 'Back L',        hue: 185, x: -0.16, y: 2.60, z: -0.22, front: false },
  'back-r':        { label: 'Back R',        hue: 285, x:  0.16, y: 2.60, z: -0.22, front: false },
  'lowerback-l':   { label: 'Low Back L',    hue:  95, x: -0.16, y: 2.12, z: -0.22, front: false },
  'lowerback-r':   { label: 'Low Back R',    hue:  25, x:  0.16, y: 2.12, z: -0.22, front: false },
  'hip-l':         { label: 'Hip L',         hue: 110, x: -0.14, y: 1.76, z:  0.18, front: true  },
  'hip-r':         { label: 'Hip R',         hue:  20, x:  0.14, y: 1.76, z:  0.18, front: true  },
  'upper-leg-l':   { label: 'Upper Leg L',   hue: 280, x: -0.12, y: 1.28, z:  0.14, front: true  },
  'upper-leg-r':   { label: 'Upper Leg R',   hue: 160, x:  0.12, y: 1.28, z:  0.14, front: true  },
  'lower-leg-l':   { label: 'Lower Leg L',   hue:  45, x: -0.10, y: 0.68, z:  0.12, front: true  },
  'lower-leg-r':   { label: 'Lower Leg R',   hue: 240, x:  0.10, y: 0.68, z:  0.12, front: true  },
  'foot-l':        { label: 'Foot L',        hue: 150, x: -0.10, y: 0.04, z:  0.10, front: true  },
  'foot-r':        { label: 'Foot R',        hue: 320, x:  0.10, y: 0.04, z:  0.10, front: true  },
}

// Colour for UI elements (CSS string) — hue from zone config, brightness from %
function zoneColorStr(pct: number, hue: number): string {
  const t   = Math.min(pct / 35, 1)
  const sat = Math.round(72 + t * 18)   // 72 → 90 %
  const lig = Math.round(42 + t * 20)   // 42 → 62 % (min raised so dark zones still pop)
  return `hsl(${hue}, ${sat}%, ${lig}%)`
}

// Colour for Three.js vertex (hex int) — same logic, different output format
function zoneColorHex(pct: number, hue: number): number {
  const t   = Math.min(pct / 35, 1)
  const sat = (72 + t * 18) / 100
  const lig = (42 + t * 20) / 100
  const a   = sat * Math.min(lig, 1 - lig)
  const f   = (n: number) => {
    const k = (n + hue / 30) % 12
    return lig - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))
  }
  const r = Math.round(f(0) * 255)
  const g = Math.round(f(8) * 255)
  const b = Math.round(f(4) * 255)
  return (r << 16) | (g << 8) | b
}

// Flat vivid body colour — fixed brightness so each zone reads as a solid block
// (percentage is shown in labels/sidebar only, not baked into the body mesh)
function zoneBodyHex(hue: number): number {
  const sat = 0.82
  const lig = 0.54
  const a   = sat * Math.min(lig, 1 - lig)
  const f   = (n: number) => {
    const k = (n + hue / 30) % 12
    return lig - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))
  }
  const r = Math.round(f(0) * 255)
  const g = Math.round(f(8) * 255)
  const b = Math.round(f(4) * 255)
  return (r << 16) | (g << 8) | b
}

// ── Per-fragment zone material ───────────────────────────────────────
// Classifying each PIXEL (not each face) makes zone boundaries pixel-perfect
// smooth instead of jagged low-poly staircases. The body's normalized coords
// (normX, normY, normZ) are baked per-vertex as `aBodyCoord`; the fragment
// shader interpolates them and runs the SAME zone logic as assignZoneId().
//
// zoneHue() / zhsl() below are GLSL ports of assignZoneId() + zoneBodyHex().
const ZONE_GLSL = /* glsl */`
float zoneHue(float nx, float ny, float nz){
  float ax = abs(nx);
  if(ny>0.88) return 270.0;
  if(ny>0.82) return 35.0;
  if(ny>0.50 && ax>0.22){
    if(ax<0.36) return nx<0.0?200.0:140.0;
    if(ax<0.54) return nx<0.0?35.0:300.0;
    if(ax<0.70) return nx<0.0?170.0:95.0;
    return nx<0.0?330.0:250.0;
  }
  if(ny>0.65){
    if(nz>=0.0) return nx<0.0?220.0:8.0;
    if(ax<0.10) return 50.0;
    return nx<0.0?185.0:285.0;
  }
  if(ny>0.50){
    if(nz>=0.0) return nx<0.0?315.0:175.0;
    return nx<0.0?95.0:25.0;
  }
  if(ny>0.38) return nx<0.0?110.0:20.0;
  if(ny>0.22) return nx<0.0?280.0:160.0;
  if(ny>0.07) return nx<0.0?45.0:240.0;
  return nx<0.0?150.0:320.0;
}
float zchan(float n, float h, float a, float l){
  float k = mod(n + h*12.0, 12.0);
  return l - a*max(-1.0, min(min(k-3.0, 9.0-k), 1.0));
}
vec3 zhsl(float h, float s, float l){      // h in [0,1]
  float a = s*min(l, 1.0-l);
  return vec3(zchan(0.0,h,a,l), zchan(8.0,h,a,l), zchan(4.0,h,a,l));
}`

function makeZoneMaterial(): any {
  const mat = new THREE.MeshLambertMaterial()
  mat.onBeforeCompile = (shader: any) => {
    shader.vertexShader =
      'attribute vec3 aBodyCoord;\nvarying vec3 vBodyCoord;\n' +
      shader.vertexShader.replace(
        'void main() {',
        'void main() {\n  vBodyCoord = aBodyCoord;'
      )
    shader.fragmentShader =
      'varying vec3 vBodyCoord;\n' + ZONE_GLSL + '\n' +
      shader.fragmentShader.replace(
        '#include <color_fragment>',
        `#include <color_fragment>
        {
          float h = zoneHue(vBodyCoord.x, vBodyCoord.y, vBodyCoord.z) / 360.0;
          vec3 srgb = zhsl(h, 0.82, 0.54);
          diffuseColor.rgb = pow(srgb, vec3(2.2));   // sRGB → linear
        }`
      )
  }
  return mat
}

// ── 3D Body Builder ─────────────────────────────────────────────────

const TARGET_HEIGHT = 3.6  // world-unit height the model is scaled to
const LOOK_AT_Y     = TARGET_HEIGHT * 0.52  // camera focal point (slightly above mid)

// Iterable array derived from ZONE_CONFIG — used by the label overlay loop
const ZONE_ANCHORS = Object.entries(ZONE_CONFIG).map(([id, cfg]) => ({ id, ...cfg }))

// Map a normalized body coordinate to one of the 23 zone ids.
//   normY: 0 (feet) → 1 (head top);  normX: -0.5 (left) → +0.5 (right);  normZ: world z relative to centre (>0 front)
function assignZoneId(normX: number, normY: number, normZ: number): string {
  const absX = Math.abs(normX)
  if (normY > 0.88) return 'head'
  if (normY > 0.82) return 'neck'
  if (normY > 0.50 && absX > 0.22) {
    const side = normX < 0 ? 'l' : 'r'
    if (absX < 0.36) return `shoulder-${side}`
    if (absX < 0.54) return `upper-arm-${side}`
    if (absX < 0.70) return `forearm-${side}`
    return `hand-${side}`
  }
  // Upper torso: chest (front) / shoulder-blade back (back)
  if (normY > 0.65) {
    if (normZ >= 0) return normX < 0 ? 'chest-l' : 'chest-r'
    return absX < 0.10 ? 'spine' : (normX < 0 ? 'back-l' : 'back-r')
  }
  // Lower torso: abdomen (front) / lower back (back)
  if (normY > 0.50) {
    if (normZ >= 0) return normX < 0 ? 'abdomen-l' : 'abdomen-r'
    return normX < 0 ? 'lowerback-l' : 'lowerback-r'
  }
  if (normY > 0.38) return normX < 0 ? 'hip-l' : 'hip-r'
  if (normY > 0.22) return normX < 0 ? 'upper-leg-l' : 'upper-leg-r'
  if (normY > 0.07) return normX < 0 ? 'lower-leg-l' : 'lower-leg-r'
  return normX < 0 ? 'foot-l' : 'foot-r'
}

function buildBodyModel(
  scene: any,
  _zones: BodyZone[],
  onLoaded: () => void,
  onError: (err: any) => void,
  onAnterior?: (sign: number) => void,
) {
  if (!THREE || typeof window === 'undefined') return

  const loader = new GLTFLoader()
  loader.load(
    '/male_model.glb',
    (gltf: any) => {
      const model = gltf.scene
      model.updateMatrixWorld(true)

      // ── 1. Identify the body mesh (most vertices) and hide the props ─────
      // GLB contains "mesh" (1226 verts, body) + "Axe"/"Pickaxe" collision
      // props (143 / 237 verts). Pick the largest mesh as the body.
      const meshes: any[] = []
      model.traverse((c: any) => { if (c.isMesh && c.geometry) meshes.push(c) })
      let bodyMesh = meshes[0]
      for (const m of meshes) {
        if ((m.geometry.attributes.position?.count ?? 0) >
            (bodyMesh.geometry.attributes.position?.count ?? 0)) bodyMesh = m
      }
      meshes.forEach(m => { if (m !== bodyMesh) m.visible = false })

      // ── 2. Normalise orientation so X = left-right and +Z = front ────────
      // The GLB's left-right axis is whichever HORIZONTAL axis has the larger
      // span (the arm span), and the feet/toes point toward the front. We
      // rotate the whole model so the rest of the pipeline can assume the
      // canonical frame (matches the hand-authored label anchors too).
      const bboxBody = () => new THREE.Box3().setFromObject(bodyMesh)
      let box  = bboxBody()
      let size = box.getSize(new THREE.Vector3())

      // If the wider horizontal axis is Z, rotate 90° so it becomes X.
      if (size.z > size.x) {
        model.rotateY(Math.PI / 2)
        model.updateMatrixWorld(true)
        box = bboxBody(); size = box.getSize(size)
      }
      let center = box.getCenter(new THREE.Vector3())

      // Feet (lowest 7%) extend toward the front → decide the +Z direction.
      {
        const posA = bodyMesh.geometry.attributes.position
        const mwA  = bodyMesh.matrixWorld
        const t    = new THREE.Vector3()
        let footZSum = 0, footN = 0
        for (let i = 0; i < posA.count; i++) {
          t.set(posA.getX(i), posA.getY(i), posA.getZ(i)).applyMatrix4(mwA)
          if ((t.y - box.min.y) / size.y < 0.07) { footZSum += t.z; footN++ }
        }
        if (footN && (footZSum / footN - center.z) < 0) {
          model.rotateY(Math.PI)          // front was -Z → spin 180°
          model.updateMatrixWorld(true)
          box = bboxBody(); size = box.getSize(size); center = box.getCenter(center)
        }
      }
      onAnterior?.(1)   // model is now canonical: front = +Z

      // ── 3. Bake per-vertex normalized body coords for the shader ────────
      // The fragment shader classifies each pixel from the interpolated coord,
      // so boundaries are smooth (no per-face staircase, no un-indexing).
      const geom = bodyMesh.geometry
      const pos  = geom.attributes.position
      const mw   = bodyMesh.matrixWorld
      const bodyCoord = new Float32Array(pos.count * 3)
      const v = new THREE.Vector3()

      for (let i = 0; i < pos.count; i++) {
        v.set(pos.getX(i), pos.getY(i), pos.getZ(i)).applyMatrix4(mw)
        bodyCoord[i * 3]     = (v.x - center.x)  / size.x   // normX
        bodyCoord[i * 3 + 1] = (v.y - box.min.y) / size.y   // normY
        bodyCoord[i * 3 + 2] =  v.z - center.z               // normZ (>0 = front)
      }

      geom.setAttribute('aBodyCoord', new THREE.BufferAttribute(bodyCoord, 3))
      bodyMesh.material = makeZoneMaterial()

      // ── 4. Scale to TARGET_HEIGHT and centre (feet at y=0) ───────────────
      const scaleFactor = TARGET_HEIGHT / size.y
      model.scale.setScalar(scaleFactor)
      model.position.x = -scaleFactor * center.x
      model.position.z = -scaleFactor * center.z
      model.position.y = -scaleFactor * box.min.y

      model.name = 'RealisticBody'
      scene.add(model)
      onLoaded()
    },
    undefined,
    onError,
  )
}

// ── 2D SVG Fallback ─────────────────────────────────────────────────

function Body2DFallback({ zones }: { zones: BodyZone[] }) {
  const [hovered, setHovered] = useState<string | null>(null)

  // SVG front-view (300×400): -l zones on LEFT, -r on RIGHT.
  // Back zones (spine, back-l, back-r) have no position → skipped in front view.
  const zonePositions: Record<string, { x: number; y: number; w: number; h: number }> = {
    'head':         { x: 130, y:   8, w:  40, h: 44 },
    'neck':         { x: 141, y:  54, w:  18, h: 20 },
    'chest-l':      { x: 115, y:  78, w:  35, h: 52 },
    'chest-r':      { x: 150, y:  78, w:  35, h: 52 },
    'abdomen-l':    { x: 115, y: 130, w:  35, h: 38 },
    'abdomen-r':    { x: 150, y: 130, w:  35, h: 38 },
    'shoulder-l':   { x:  68, y:  80, w:  42, h: 24 },
    'shoulder-r':   { x: 190, y:  80, w:  42, h: 24 },
    'upper-arm-l':  { x:  68, y: 104, w:  40, h: 26 },
    'upper-arm-r':  { x: 192, y: 104, w:  40, h: 26 },
    'forearm-l':    { x:  70, y: 130, w:  38, h: 26 },
    'forearm-r':    { x: 192, y: 130, w:  38, h: 26 },
    'hand-l':       { x:  72, y: 156, w:  35, h: 16 },
    'hand-r':       { x: 193, y: 156, w:  35, h: 16 },
    'hip-l':        { x: 115, y: 170, w:  35, h: 52 },
    'hip-r':        { x: 150, y: 170, w:  35, h: 52 },
    'upper-leg-l':  { x: 119, y: 224, w:  26, h: 88 },
    'upper-leg-r':  { x: 155, y: 224, w:  26, h: 88 },
    'lower-leg-l':  { x: 121, y: 314, w:  23, h: 65 },
    'lower-leg-r':  { x: 156, y: 314, w:  23, h: 65 },
    'foot-l':       { x: 115, y: 381, w:  28, h: 12 },
    'foot-r':       { x: 156, y: 381, w:  28, h: 12 },
  }

  return (
    <svg viewBox="0 0 300 400" style={{ width: '100%', maxWidth: 300, height: 'auto' }}>
      {/* Body outline */}
      <g opacity="0.2" stroke="var(--c-wire-s)" strokeWidth="1" fill="none">
        {/* Head */}
        <circle cx="150" cy="32" r="22" />
        {/* Neck */}
        <rect x="143" y="55" width="14" height="18" rx="3" />
        {/* Torso */}
        <rect x="115" y="78" width="70" height="90" rx="6" />
        {/* Arms */}
        <rect x="70" y="82" width="38" height="75" rx="10" />
        <rect x="192" y="82" width="38" height="75" rx="10" />
        {/* Hips */}
        <rect x="115" y="170" width="70" height="50" rx="4" />
        {/* Legs */}
        <rect x="120" y="225" width="25" height="85" rx="8" />
        <rect x="155" y="225" width="25" height="85" rx="8" />
        {/* Calves */}
        <rect x="122" y="315" width="22" height="65" rx="7" />
        <rect x="157" y="315" width="22" height="65" rx="7" />
      </g>

      {/* Zone overlays */}
      {zones.map(zone => {
        const pos = zonePositions[zone.id]
        if (!pos) return null
        const isHovered = hovered === zone.id

        return (
          <g
            key={zone.id}
            onMouseEnter={() => setHovered(zone.id)}
            onMouseLeave={() => setHovered(null)}
            style={{ cursor: 'pointer' }}
          >
            <rect
              x={pos.x}
              y={pos.y}
              width={pos.w}
              height={pos.h}
              rx={8}
              fill={zoneColorStr(zone.percentage, ZONE_CONFIG[zone.id]?.hue ?? 180)}
              opacity={isHovered ? 0.9 : 0.6}
              stroke={isHovered ? '#fff' : 'transparent'}
              strokeWidth={1.5}
              style={{ transition: 'opacity 0.2s' }}
            />
            <text
              x={pos.x + pos.w / 2}
              y={pos.y + pos.h / 2 + 4}
              textAnchor="middle"
              fill="#fff"
              fontSize="12"
              fontWeight="700"
              fontFamily="monospace"
              style={{ pointerEvents: 'none' }}
            >
              {zone.percentage}%
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ── Main Component ──────────────────────────────────────────────────

export default function BodySegmentation3D({ zones = BODY_ZONES }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const labelsCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const rendererRef = useRef<any>(null)
  const sceneRef = useRef<any>(null)
  const cameraRef = useRef<any>(null)
  const animRef = useRef<number>(0)
  const [is3DReady, setIs3DReady] = useState(false)
  const [use3D, setUse3D] = useState(true)
  const [hoveredZone, setHoveredZone] = useState<BodyZone | null>(null)
  const [showLabels, setShowLabels] = useState(true)
  // Ref copy used inside the animate-loop closure (avoids stale state)
  const showLabelsRef = useRef(true)
  // Detected anterior (forward) Z sign of the GLB model; keeps labels in sync
  // with the body's front/back colouring (set once the model loads).
  const anteriorSignRef = useRef(1)

  // Mouse interaction state — dist tracks camera distance for scroll-zoom
  const mouseRef = useRef({ down: false, prevX: 0, prevY: 0, rotX: 0.12, rotY: 0, dist: 7 })

  useEffect(() => {
    if (!use3D || !containerRef.current) return

    let cancelled = false
    const container = containerRef.current
    if (!container) return

    const width = container.clientWidth
    const height = 480

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x080808)
    sceneRef.current = scene

    // Camera — positioned to show full model (feet at y=0, top at y=TARGET_HEIGHT)
    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100)
    camera.position.set(0, LOOK_AT_Y, mouseRef.current.dist)
    camera.lookAt(0, LOOK_AT_Y, 0)
    cameraRef.current = camera

    // Renderer — NoToneMapping keeps the flat zone colours exactly as assigned
    // (ACES would desaturate / shift the hues into a washed gradient).
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.NoToneMapping
    rendererRef.current = renderer
    container.appendChild(renderer.domElement)

    // Size the 2D labels overlay canvas
    const lc = labelsCanvasRef.current
    if (lc) { lc.width = width; lc.height = height }

    // Lights — ALL NEUTRAL WHITE. Coloured lights would tint the flat zone
    // colours (blue back + green rim caused the washed blue→green gradient).
    // High ambient keeps hues true; one soft key light gives gentle 3D form.
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.82)
    scene.add(ambientLight)

    const keyLight = new THREE.DirectionalLight(0xffffff, 0.28)
    keyLight.position.set(1, 3, 4)
    scene.add(keyLight)

    const fillLight = new THREE.DirectionalLight(0xffffff, 0.14)
    fillLight.position.set(-2, 1, -3)
    scene.add(fillLight)

    // Ground grid — sits at y=0 where the model's feet land
    const gridHelper = new THREE.GridHelper(10, 20, 0x222222, 0x151515)
    gridHelper.position.y = -0.02
    scene.add(gridHelper)

    // Build body model asynchronously
    buildBodyModel(
      scene,
      zones,
      () => {
        if (!cancelled) setIs3DReady(true)
      },
      (err) => {
        console.error('Failed to load 3D model:', err)
        if (!cancelled) setUse3D(false)
      },
      (sign) => { anteriorSignRef.current = sign },
    )

    // Raycaster for hover
    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()

    const onMouseMoveRay = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

      raycaster.setFromCamera(mouse, camera)
      
      // Ensure we check all descendants
      const intersects = raycaster.intersectObjects(scene.children, true)
      
      let foundZoneId: string | null = null
      
      if (intersects.length > 0) {
        const hit = intersects[0]
        // If it's the realistic model, use intersection point to determine zone
        if ((hit.object as any).isMesh) {
            const model = scene.getObjectByName('RealisticBody')
            if (model) {
              const box = new THREE.Box3().setFromObject(model)
              const size = box.getSize(new THREE.Vector3())
              const center = box.getCenter(new THREE.Vector3())

              // Hit point in world space → same normalisation the colouring uses
              const normY  = (hit.point.y - box.min.y) / size.y
              const normX  = (hit.point.x - center.x)  / size.x
              const facing = (hit.point.z - center.z)  * anteriorSignRef.current

              foundZoneId = assignZoneId(normX, normY, facing)
            }
        }
      }
      
      if (foundZoneId) {
        const found = zones.find(z => z.id === foundZoneId)
        setHoveredZone(found || null)
      } else {
        setHoveredZone(null)
      }
    }

    container.addEventListener('mousemove', onMouseMoveRay)

    // Mouse rotation controls
    const onMouseDown = (e: MouseEvent) => {
      mouseRef.current.down = true
      mouseRef.current.prevX = e.clientX
      mouseRef.current.prevY = e.clientY
    }

    const onMouseMove = (e: MouseEvent) => {
      if (!mouseRef.current.down) return
      const dx = e.clientX - mouseRef.current.prevX
      const dy = e.clientY - mouseRef.current.prevY
      mouseRef.current.rotY += dx * 0.008
      mouseRef.current.rotX += dy * 0.005
      mouseRef.current.rotX = Math.max(-0.5, Math.min(0.8, mouseRef.current.rotX))
      mouseRef.current.prevX = e.clientX
      mouseRef.current.prevY = e.clientY
    }

    const onMouseUp = () => { mouseRef.current.down = false }

    container.addEventListener('mousedown', onMouseDown)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)

    // Scroll zoom — store distance separately so the animate loop can use it
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      mouseRef.current.dist = Math.max(4, Math.min(12, mouseRef.current.dist + e.deltaY * 0.005))
    }
    container.addEventListener('wheel', onWheel, { passive: false })

    // ── Zone label overlay — back-face culled + edge-anchored columns ────
    // Labels are stacked down the left/right edges (no overlap) with leader
    // lines to each body point, matching a medical-style segmentation diagram.
    const drawZoneLabels = (cam: any) => {
      const canvas = labelsCanvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      const w = canvas.width
      const h = canvas.height
      ctx.clearRect(0, 0, w, h)
      if (!showLabelsRef.current) return

      const BOX_W = 104
      const BOX_H = 30
      const PAD_Y = 5            // min vertical gap between stacked boxes
      const SLOT  = BOX_H + PAD_Y

      // Camera's horizontal viewing direction (body is centred on x=z=0)
      const camDir = Math.hypot(cam.position.x, cam.position.z) || 1
      const cdx = cam.position.x / camDir
      const cdz = cam.position.z / camDir

      // Build the visible set (cull zones whose surface faces away)
      type Lbl = { label: string; pct: number; color: string; sx: number; sy: number }
      const left: Lbl[]  = []
      const right: Lbl[] = []

      // Flip anchor Z to match the body's detected front/back orientation
      const aSign = anteriorSignRef.current

      for (const anchor of ZONE_ANCHORS) {
        const az = anchor.z * aSign
        // Outward surface normal (horizontal) ≈ direction of anchor from axis
        const nLen = Math.hypot(anchor.x, az) || 1
        const nx = anchor.x / nLen
        const nz = az / nLen
        // Facing camera when normal·cameraDir > margin
        if (nx * cdx + nz * cdz < -0.15) continue

        const v = new THREE.Vector3(anchor.x, anchor.y, az)
        v.project(cam)
        if (v.z > 1) continue
        const sx = (v.x + 1) / 2 * w
        const sy = (-v.y + 1) / 2 * h

        const zone  = zones.find(z => z.id === anchor.id)
        const pct   = zone?.percentage ?? 0
        const color = zoneColorStr(50, ZONE_CONFIG[anchor.id]?.hue ?? 180)
        const item: Lbl = { label: anchor.label, pct, color, sx, sy }
        ;(sx < w / 2 ? left : right).push(item)
      }

      // Distribute boxes down an edge without overlapping
      const layout = (items: Lbl[], edgeX: number, isLeft: boolean) => {
        items.sort((a, b) => a.sy - b.sy)
        const ys = items.map(it => Math.max(4, Math.min(h - BOX_H - 4, it.sy - BOX_H / 2)))
        for (let i = 1; i < ys.length; i++) {
          if (ys[i] < ys[i - 1] + SLOT) ys[i] = ys[i - 1] + SLOT
        }
        const overflow = ys.length ? (ys[ys.length - 1] + BOX_H + 4 - h) : 0
        if (overflow > 0) for (let i = 0; i < ys.length; i++) ys[i] = Math.max(4, ys[i] - overflow)

        items.forEach((it, i) => {
          const by = ys[i]
          const lineStartX = isLeft ? edgeX + BOX_W : edgeX
          const lineStartY = by + BOX_H / 2

          // Leader line: box → anchor dot
          ctx.strokeStyle = 'rgba(255,255,255,0.28)'
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(lineStartX, lineStartY)
          ctx.lineTo(it.sx, it.sy)
          ctx.stroke()

          // Anchor dot
          ctx.fillStyle = it.color
          ctx.beginPath()
          ctx.arc(it.sx, it.sy, 3, 0, Math.PI * 2)
          ctx.fill()

          // Box
          const r = 4
          ctx.fillStyle = 'rgba(10,10,14,0.92)'
          ctx.strokeStyle = it.color
          ctx.lineWidth = 1.25
          ctx.beginPath()
          ctx.moveTo(edgeX + r, by)
          ctx.lineTo(edgeX + BOX_W - r, by)
          ctx.quadraticCurveTo(edgeX + BOX_W, by, edgeX + BOX_W, by + r)
          ctx.lineTo(edgeX + BOX_W, by + BOX_H - r)
          ctx.quadraticCurveTo(edgeX + BOX_W, by + BOX_H, edgeX + BOX_W - r, by + BOX_H)
          ctx.lineTo(edgeX + r, by + BOX_H)
          ctx.quadraticCurveTo(edgeX, by + BOX_H, edgeX, by + BOX_H - r)
          ctx.lineTo(edgeX, by + r)
          ctx.quadraticCurveTo(edgeX, by, edgeX + r, by)
          ctx.closePath()
          ctx.fill()
          ctx.stroke()

          // Colour swatch
          ctx.fillStyle = it.color
          ctx.fillRect(edgeX + 7, by + 9, 11, 11)

          // Name + percentage
          ctx.fillStyle = 'rgba(190,190,205,0.95)'
          ctx.font = '8.5px system-ui, sans-serif'
          ctx.fillText(it.label.toUpperCase(), edgeX + 23, by + 13)
          ctx.fillStyle = it.color
          ctx.font = 'bold 12px system-ui, monospace'
          ctx.fillText(`${it.pct}%`, edgeX + 23, by + 25)
        })
      }

      layout(left, 6, true)
      layout(right, w - BOX_W - 6, false)
    }

    // Animation loop
    const animate = () => {
      animRef.current = requestAnimationFrame(animate)

      const rY   = mouseRef.current.rotY
      const rX   = mouseRef.current.rotX
      const dist = mouseRef.current.dist

      // Orbit camera around the model centre
      camera.position.x = dist * Math.sin(rY)
      camera.position.z = dist * Math.cos(rY)
      camera.position.y = LOOK_AT_Y + rX * 3
      camera.lookAt(0, LOOK_AT_Y, 0)

      renderer.render(scene, camera)
      drawZoneLabels(camera)
    }
    animate()

    // Resize handler
    const onResize = () => {
      const w = container.clientWidth
      const h = 480
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
      const lc2 = labelsCanvasRef.current
      if (lc2) { lc2.width = w; lc2.height = h }
    }
    window.addEventListener('resize', onResize)

    // Cleanup
    return () => {
      cancelled = true
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
      window.removeEventListener('resize', onResize)
      container.removeEventListener('mousedown', onMouseDown)
      container.removeEventListener('mousemove', onMouseMoveRay)
      container.removeEventListener('wheel', onWheel)
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement)
      }
      renderer.dispose()
    }
  }, [use3D, zones])

  // Sort zones by percentage for the sidebar
  const sortedZones = useMemo(() =>
    [...zones].sort((a, b) => b.percentage - a.percentage),
    [zones]
  )

  return (
    <div style={{
      background: 'var(--c-panel)',
      border: '1px solid var(--c-wire)',
      borderRadius: 10,
      padding: '20px 16px',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
      }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--c-ink)', marginBottom: 2 }}>
            Body Zone Exposure
          </div>
          <div style={{ fontSize: 12, color: 'var(--c-ghost)' }}>
            {use3D ? 'Interactive 3D model — drag to rotate, scroll to zoom' : '2D body map visualization'}
          </div>
        </div>
        <button
          onClick={() => setUse3D(v => !v)}
          style={{
            background: 'none',
            border: '1px solid var(--c-wire)',
            borderRadius: 6,
            color: 'var(--c-dim)',
            padding: '6px 12px',
            fontSize: 11,
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--c-wire-s)'; e.currentTarget.style.color = 'var(--c-ink)' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--c-wire)'; e.currentTarget.style.color = 'var(--c-dim)' }}
        >
          {use3D ? '⬜ Switch to 2D' : '🧊 Switch to 3D'}
        </button>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: use3D ? '1fr 280px' : '300px 1fr',
        gap: 24,
        alignItems: 'start',
      }}>
        {/* 3D Canvas or 2D SVG */}
        <div style={{ order: use3D ? 0 : 0 }}>
          {use3D ? (
            <div
              ref={containerRef}
              className="canvas-3d"
              style={{
                width: '100%',
                height: 480,
                background: '#080808',
                borderRadius: 10,
                border: '1px solid var(--c-wire)',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {/* 2D labels overlay — drawn every frame, pointer-events off */}
              <canvas
                ref={labelsCanvasRef}
                style={{
                  position: 'absolute',
                  inset: 0,
                  pointerEvents: 'none',
                  zIndex: 5,
                }}
              />

              {/* Toggle zone stats */}
              {is3DReady && (
                <button
                  onClick={() => {
                    const next = !showLabels
                    setShowLabels(next)
                    showLabelsRef.current = next
                  }}
                  style={{
                    position: 'absolute',
                    top: 10,
                    right: 10,
                    zIndex: 10,
                    background: showLabels ? 'rgba(22,22,32,0.92)' : 'rgba(14,14,20,0.75)',
                    border: `1px solid ${showLabels ? 'var(--c-wire-s)' : 'var(--c-wire)'}`,
                    borderRadius: 6,
                    color: showLabels ? 'var(--c-ink)' : 'var(--c-ghost)',
                    padding: '5px 11px',
                    fontSize: 11,
                    fontWeight: 500,
                    cursor: 'pointer',
                    letterSpacing: '0.04em',
                    backdropFilter: 'blur(6px)',
                    transition: 'all 0.15s',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <span style={{
                    display: 'inline-block',
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    background: showLabels ? 'var(--c-spark)' : 'var(--c-ghost)',
                    transition: 'background 0.15s',
                  }} />
                  {showLabels ? 'Stats On' : 'Stats Off'}
                </button>
              )}

              {!is3DReady && (
                <div style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--c-ghost)',
                  fontSize: 12,
                }}>
                  <div className="spin" style={{ width: 20, height: 20, border: '2px solid var(--c-wire)', borderTopColor: 'var(--c-spark)', borderRadius: '50%', marginRight: 10 }} />
                  Loading 3D model…
                </div>
              )}

              {/* Hover tooltip */}
              {hoveredZone && (
                <div style={{
                  position: 'absolute',
                  bottom: 16,
                  left: 16,
                  background: 'rgba(14,14,14,0.9)',
                  backdropFilter: 'blur(8px)',
                  border: '1px solid var(--c-wire-s)',
                  borderRadius: 8,
                  padding: '10px 14px',
                  zIndex: 10,
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--c-ink)', marginBottom: 3 }}>
                    {hoveredZone.name}
                  </div>
                  <div className="num" style={{
                    fontSize: 22,
                    fontWeight: 700,
                    color: zoneColorStr(hoveredZone.percentage, ZONE_CONFIG[hoveredZone.id]?.hue ?? 180),
                  }}>
                    {hoveredZone.percentage}%
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              padding: '20px 0',
              background: '#0a0a0a',
              borderRadius: 10,
              border: '1px solid var(--c-wire)',
            }}>
              <Body2DFallback zones={zones} />
            </div>
          )}
        </div>

        {/* Zone list sidebar */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
          order: 1,
        }}>
          <div style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--c-ghost)',
            marginBottom: 6,
            paddingLeft: 10,
          }}>
            Zone Breakdown
          </div>

          {sortedZones.map((zone, i) => {
            const isHovered = hoveredZone?.id === zone.id

            return (
              <div
                key={zone.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 10px',
                  borderRadius: 6,
                  background: isHovered ? 'var(--c-hover)' : 'transparent',
                  transition: 'background 0.15s',
                }}
              >
                {/* Rank */}
                <span className="num" style={{
                  fontSize: 10,
                  color: 'var(--c-ghost)',
                  width: 16,
                  textAlign: 'center',
                }}>
                  {i + 1}
                </span>

                {/* Color dot — unique hue per zone */}
                <div style={{
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background: zoneColorStr(zone.percentage, ZONE_CONFIG[zone.id]?.hue ?? 180),
                  flexShrink: 0,
                }} />

                {/* Name */}
                <div style={{
                  flex: 1,
                  fontSize: 12,
                  color: isHovered ? 'var(--c-ink)' : 'var(--c-dim)',
                  transition: 'color 0.15s',
                }}>
                  {zone.name}
                </div>

                {/* Bar */}
                <div style={{
                  width: 60,
                  height: 4,
                  background: 'var(--c-wire)',
                  borderRadius: 2,
                  overflow: 'hidden',
                  flexShrink: 0,
                }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(100, (zone.percentage / 35) * 100)}%`,
                    background: zoneColorStr(zone.percentage, ZONE_CONFIG[zone.id]?.hue ?? 180),
                    borderRadius: 2,
                    transition: 'width 0.6s ease',
                  }} />
                </div>

                {/* Percentage */}
                <span className="num" style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: zoneColorStr(zone.percentage, ZONE_CONFIG[zone.id]?.hue ?? 180),
                  minWidth: 42,
                  textAlign: 'right',
                }}>
                  {zone.percentage}%
                </span>
              </div>
            )
          })}

          {/* Zone colour key — one swatch per zone replacing the old single-gradient heat scale */}
          <div style={{
            marginTop: 16,
            padding: '10px 10px',
            borderTop: '1px solid var(--c-wire)',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '6px 10px',
          }}>
            {ZONE_ANCHORS.map(a => (
              <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: 2,
                  background: zoneColorStr(50, a.hue),
                }} />
                <span style={{ fontSize: 9, color: 'var(--c-ghost)', letterSpacing: '0.04em' }}>
                  {a.label.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
