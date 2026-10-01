import React, { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Html, Line, OrbitControls } from '@react-three/drei'
import * as THREE from 'three'

/**
 * Lightweight hero network for the landing page.
 * Seven representative nodes with travelling data packets, auto-rotating.
 */

const HERO_NODES = [
  { id: 'internet', label: 'Internet', type: 'cloud', position: [-7.4, 2.6, -1.2] },
  { id: 'users', label: 'User Devices', type: 'client', position: [-7.0, -2.8, 2.6] },
  { id: 'firewall', label: 'Firewall', type: 'firewall', position: [-3.4, 0.2, -0.4] },
  { id: 'web', label: 'Web Server', type: 'server', position: [0.4, 3.0, -2.4] },
  { id: 'api', label: 'API Server', type: 'server', position: [0.6, -0.2, 1.4] },
  { id: 'db', label: 'Database', type: 'database', position: [4.6, -2.2, -0.6] },
  { id: 'ai', label: 'AI Security Engine', type: 'ai', position: [4.8, 2.6, 2.4] },
]

const HERO_EDGES = [
  ['internet', 'firewall'],
  ['users', 'firewall'],
  ['firewall', 'web'],
  ['firewall', 'api'],
  ['web', 'api'],
  ['api', 'db'],
  ['ai', 'web'],
  ['ai', 'db'],
  ['ai', 'firewall'],
]

function geom(type) {
  switch (type) {
    case 'cloud':
      return <sphereGeometry args={[0.95, 14, 10]} />
    case 'firewall':
      return <boxGeometry args={[1.3, 1.3, 0.32]} />
    case 'server':
      return <boxGeometry args={[1.05, 1.2, 1.05]} />
    case 'database':
      return <cylinderGeometry args={[0.75, 0.75, 1.2, 14]} />
    case 'client':
      return <octahedronGeometry args={[0.82, 0]} />
    case 'ai':
      return <icosahedronGeometry args={[0.88, 0]} />
    default:
      return <sphereGeometry args={[0.8, 12, 8]} />
  }
}

function HeroGroup({ compact }) {
  const group = useRef()
  const map = useMemo(() => Object.fromEntries(HERO_NODES.map((n) => [n.id, n.position])), [])
  const edges = useMemo(() => HERO_EDGES.map(([a, b]) => [map[a], map[b]]).filter(Boolean), [map])

  const packets = useRef(
    Array.from({ length: compact ? 10 : 16 }, (_, i) => ({
      edge: i % HERO_EDGES.length,
      t: Math.random(),
      speed: 0.14 + Math.random() * 0.24,
      reverse: i % 2 === 0,
    })),
  )
  const refs = useRef([])

  useFrame((state, delta) => {
    if (group.current) group.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.12) * 0.34
    packets.current.forEach((p, i) => {
      const mesh = refs.current[i]
      if (!mesh) return
      p.t = (p.t + delta * p.speed) % 1
      const e = edges[p.edge]
      if (!e) return
      const k = p.reverse ? 1 - p.t : p.t
      mesh.position.set(
        e[0][0] + (e[1][0] - e[0][0]) * k,
        e[0][1] + (e[1][1] - e[0][1]) * k,
        e[0][2] + (e[1][2] - e[0][2]) * k,
      )
    })
  })

  return (
    <group ref={group}>
      {edges.map((e, i) => (
        <Line key={i} points={e} color="#1f4d6b" lineWidth={1.1} dashed dashSize={0.25} gapSize={0.35} />
      ))}
      {HERO_NODES.map((n) => (
        <group key={n.id} position={n.position}>
          <mesh>
            {geom(n.type)}
            <meshStandardMaterial
              color="#38d6f5"
              emissive="#12b6dd"
              emissiveIntensity={n.id === 'ai' ? 0.7 : 0.32}
              roughness={0.4}
              metalness={0.3}
            />
          </mesh>
          <mesh>
            <sphereGeometry args={[1.15, 14, 10]} />
            <meshBasicMaterial color="#38d6f5" transparent opacity={0.07} depthWrite={false} />
          </mesh>
          {!compact && (
            <Html position={[0, 1.35, 0]} center distanceFactor={8} style={{ pointerEvents: 'none' }}>
              <div className="whitespace-nowrap rounded border border-cyber-400/25 bg-ink-950/80 px-1.5 py-0.5 text-[9.5px] font-medium text-slate-200">
                {n.label}
              </div>
            </Html>
          )}
        </group>
      ))}
      {packets.current.map((_, i) => (
        <mesh
          key={i}
          ref={(el) => {
            refs.current[i] = el
          }}
        >
          <sphereGeometry args={[0.07, 8, 8]} />
          <meshBasicMaterial color="#7ee7ff" />
        </mesh>
      ))}
    </group>
  )
}

export default function HeroScene({ compact = false }) {
  return (
    <Canvas
      dpr={[1, 1.6]}
      camera={{ position: [0.5, 3.6, 12.5], fov: 46 }}
      gl={{ antialias: true, alpha: true }}
      style={{ background: 'transparent' }}
    >
      <ambientLight intensity={0.6} />
      <directionalLight position={[6, 10, 6]} intensity={1.1} />
      <pointLight position={[-8, -4, 4]} intensity={0.55} color="#12b6dd" />
      <HeroGroup compact={compact} />
      <OrbitControls enableZoom={false} enablePan={false} autoRotate={false} enableDamping dampingFactor={0.1} />
    </Canvas>
  )
}
