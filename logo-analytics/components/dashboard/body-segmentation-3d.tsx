'use client'

import { useRef, useEffect, useState, useMemo } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { BodyZone } from '@/lib/types'
import { BODY_ZONES } from '@/lib/mock-data'

interface Props {
  zones?: BodyZone[]
}

// Color interpolation: percentage → hsl
function percentToColor(pct: number): string {
  // 0% → cool blue (200, 70, 50), 35%+ → hot red/yellow
  const maxPct = 35
  const t = Math.min(pct / maxPct, 1)
  const hue = 200 - t * 200 // from 200 (blue) → 0 (red)
  const sat = 70 + t * 20
  const lig = 45 + t * 15
  return `hsl(${Math.round(hue)}, ${Math.round(sat)}%, ${Math.round(lig)}%)`
}

function percentToHex(pct: number): number {
  const maxPct = 35
  const t = Math.min(pct / maxPct, 1)
  const hue = 200 - t * 200
  const sat = (70 + t * 20) / 100
  const lig = (45 + t * 15) / 100

  // HSL → RGB
  const a = sat * Math.min(lig, 1 - lig)
  const f = (n: number) => {
    const k = (n + hue / 30) % 12
    return lig - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))
  }
  const r = Math.round(f(0) * 255)
  const g = Math.round(f(8) * 255)
  const b = Math.round(f(4) * 255)
  return (r << 16) | (g << 8) | b
}

// ── 3D Body Builder ─────────────────────────────────────────────────

const TARGET_HEIGHT = 3.6  // world-unit height the model is scaled to
const LOOK_AT_Y     = TARGET_HEIGHT * 0.52  // camera focal point (slightly above mid)

function buildBodyModel(scene: any, zones: BodyZone[], onLoaded: () => void, onError: (err: any) => void) {
  if (!THREE || typeof window === 'undefined') return

  const zoneMap: Record<string, number> = {}
  zones.forEach(z => { zoneMap[z.id] = z.percentage })

  const loader = new GLTFLoader()
  loader.load(
    '/male_model.glb',
    (gltf: any) => {
      const model = gltf.scene

      // Must call this before Box3 or matrixWorld usage —
      // GLTFLoader applies a -90° X rotation (Blender→GLTF) that isn't
      // propagated to matrixWorld until the first updateMatrixWorld pass.
      model.updateMatrixWorld(true)

      // ── 1. Bounding box in world space (after matrix update) ─────────────
      const box    = new THREE.Box3().setFromObject(model)
      const size   = box.getSize(new THREE.Vector3())
      const center = box.getCenter(new THREE.Vector3())

      // ── 2. Hide known props by node name; colour the body mesh ───────────
      // GLB node names: "Axe-colonly", "Pickaxe-colonly" → props to hide.
      // "mesh" (node[57], 1226 verts, skinned) → the actual body.
      model.traverse((child: any) => {
        if (!child.isMesh || !child.geometry) return

        const name = (child.name ?? '').toLowerCase()
        if (name.includes('axe') || name.includes('pickaxe') ||
            name.includes('weapon') || name.includes('prop')) {
          child.visible = false
          return
        }

        // Assign zone vertex colours to the body mesh
        const pos    = child.geometry.attributes.position
        const colors: number[] = []

        for (let i = 0; i < pos.count; i++) {
          const v = new THREE.Vector3(pos.getX(i), pos.getY(i), pos.getZ(i))
          v.applyMatrix4(child.matrixWorld)

          const normY = (v.y - box.min.y) / size.y
          const normX = (v.x - center.x)  / size.x
          const normZ =  v.z - center.z

          let zoneId = 'socks'
          if      (normY > 0.88)                          zoneId = 'head'
          else if (normY > 0.82)                          zoneId = 'collar'
          else if (normY > 0.45) {
            if      (normX >  0.22)                       zoneId = 'sleeve-l'
            else if (normX < -0.22)                       zoneId = 'sleeve-r'
            else if (normZ  >  0)                         zoneId = 'chest-front'
            else                                          zoneId = 'back'
          }
          else if (normY > 0.35)                          zoneId = 'shorts'

          const pct = zoneMap[zoneId] ?? 0
          const hex = percentToHex(pct)
          const c   = new THREE.Color(hex)
          colors.push(c.r, c.g, c.b)
        }

        child.geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
        child.material = new THREE.MeshStandardMaterial({
          vertexColors: true,
          roughness: 0.55,
          metalness: 0.05,
          transparent: true,
          opacity: 0.97,
        })
      })

      // ── 3. Scale so the model is exactly TARGET_HEIGHT units tall ─────────
      const scaleFactor = TARGET_HEIGHT / size.y
      model.scale.setScalar(scaleFactor)

      // ── 4. Centre model: feet at y=0, centred on x/z ──────────────────────
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

  const zonePositions: Record<string, { x: number; y: number; w: number; h: number }> = {
    'head':        { x: 130, y: 10,  w: 40, h: 45 },
    'collar':      { x: 128, y: 60,  w: 44, h: 18 },
    'chest-front': { x: 108, y: 82,  w: 84, h: 80 },
    'back':        { x: 112, y: 165, w: 76, h: 45 },
    'sleeve-l':    { x: 60,  y: 85,  w: 44, h: 70 },
    'sleeve-r':    { x: 196, y: 85,  w: 44, h: 70 },
    'shorts':      { x: 108, y: 215, w: 84, h: 60 },
    'socks':       { x: 118, y: 325, w: 64, h: 55 },
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
              fill={percentToColor(zone.percentage)}
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
  const rendererRef = useRef<any>(null)
  const sceneRef = useRef<any>(null)
  const cameraRef = useRef<any>(null)
  const animRef = useRef<number>(0)
  const [is3DReady, setIs3DReady] = useState(false)
  const [use3D, setUse3D] = useState(true)
  const [hoveredZone, setHoveredZone] = useState<BodyZone | null>(null)

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

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.1
    rendererRef.current = renderer
    container.appendChild(renderer.domElement)

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4)
    scene.add(ambientLight)

    const frontLight = new THREE.DirectionalLight(0xffffff, 0.8)
    frontLight.position.set(2, 4, 5)
    scene.add(frontLight)

    const backLight = new THREE.DirectionalLight(0x6688ff, 0.3)
    backLight.position.set(-2, 2, -4)
    scene.add(backLight)

    const rimLight = new THREE.PointLight(0xC5F000, 0.3, 15)
    rimLight.position.set(3, 3, 2)
    scene.add(rimLight)

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
      }
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
              
              // The hit point is in world space
              const y = hit.point.y - box.min.y
              const x = hit.point.x - center.x
              const z = hit.point.z - center.z
              
              const normY = y / size.y
              const normX = x / size.x
              
              let zoneId = 'socks'
              if (normY > 0.88) zoneId = 'head'
              else if (normY > 0.82) zoneId = 'collar'
              else if (normY > 0.45) {
                if (normX > 0.22) zoneId = 'sleeve-l'
                else if (normX < -0.22) zoneId = 'sleeve-r'
                else if (z > 0) zoneId = 'chest-front'
                else zoneId = 'back'
              }
              else if (normY > 0.35) zoneId = 'shorts'
              else zoneId = 'socks'
              
              foundZoneId = zoneId
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
    }
    animate()

    // Resize handler
    const onResize = () => {
      const w = container.clientWidth
      const h = 480
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
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
                    color: percentToColor(hoveredZone.percentage),
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

                {/* Color dot */}
                <div style={{
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background: percentToColor(zone.percentage),
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
                    background: percentToColor(zone.percentage),
                    borderRadius: 2,
                    transition: 'width 0.6s ease',
                  }} />
                </div>

                {/* Percentage */}
                <span className="num" style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: percentToColor(zone.percentage),
                  minWidth: 42,
                  textAlign: 'right',
                }}>
                  {zone.percentage}%
                </span>
              </div>
            )
          })}

          {/* Color scale legend */}
          <div style={{
            marginTop: 16,
            padding: '12px 10px',
            borderTop: '1px solid var(--c-wire)',
          }}>
            <div style={{ fontSize: 10, color: 'var(--c-ghost)', marginBottom: 6, letterSpacing: '0.06em' }}>
              HEAT SCALE
            </div>
            <div style={{
              height: 8,
              borderRadius: 4,
              background: `linear-gradient(90deg, ${percentToColor(0)}, ${percentToColor(10)}, ${percentToColor(20)}, ${percentToColor(35)})`,
            }} />
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 10,
              color: 'var(--c-ghost)',
              marginTop: 4,
            }}>
              <span>Low</span>
              <span>High</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
