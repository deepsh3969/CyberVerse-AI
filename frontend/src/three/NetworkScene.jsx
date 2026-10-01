import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Html, Line, OrbitControls } from '@react-three/drei'
import * as THREE from 'three'

export const STATUS_COLORS = {
  healthy: '#2fd98a',
  warning: '#f5c518',
  compromised: '#ff3b5c',
  monitoring: '#6f8fff',
  contained: '#38d6f5',
}

const EDGE_COLORS = { attack: '#ff3b5c', warning: '#f5c518', contained: '#38d6f5', idle: '#27405e' }

function geometryFor(type) {
  switch (type) {
    case 'cloud':
      return <sphereGeometry args={[1.05, 14, 10]} />
    case 'firewall':
      return <boxGeometry args={[1.5, 1.5, 0.35]} />
    case 'server':
      return <boxGeometry args={[1.2, 1.35, 1.2]} />
    case 'database':
      return <cylinderGeometry args={[0.85, 0.85, 1.4, 14]} />
    case 'client':
      return <octahedronGeometry args={[0.95, 0]} />
    case 'gateway':
      return <dodecahedronGeometry args={[0.95, 0]} />
    case 'security':
      return <torusGeometry args={[0.8, 0.26, 8, 18]} />
    case 'ai':
      return <icosahedronGeometry args={[0.98, 0]} />
    default:
      return <sphereGeometry args={[0.9, 12, 8]} />
  }
}

function Node3D({ node, selected, onSelect, dimmed }) {
  const [hovered, setHovered] = useState(false)
  const meshRef = useRef()
  const haloRef = useRef()
  const base = STATUS_COLORS[node.status] || '#94a3b8'
  const compromised = node.status === 'compromised'

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime
    if (meshRef.current) {
      const target = selected ? 1.18 : hovered ? 1.1 : 1
      meshRef.current.scale.lerp(new THREE.Vector3(target, target, target), 0.12)
      meshRef.current.rotation.y += delta * (node.type === 'ai' || node.type === 'security' ? 0.35 : 0.12)
      if (node.type !== 'firewall') meshRef.current.rotation.x += delta * 0.05
    }
    if (haloRef.current) {
      const pulse = compromised ? 1.55 + Math.sin(t * 4) * 0.16 : 1.42 + Math.sin(t * 1.6) * 0.05
      haloRef.current.scale.setScalar(pulse)
      haloRef.current.material.opacity = compromised ? 0.32 : selected || hovered ? 0.22 : 0.11
    }
  })

  return (
    <group position={node.position}>
      <mesh
        ref={haloRef}
        onClick={(e) => {
          e.stopPropagation()
          onSelect(node)
        }}
        onPointerOver={(e) => {
          e.stopPropagation()
          setHovered(true)
          document.body.style.cursor = 'pointer'
        }}
        onPointerOut={() => {
          setHovered(false)
          document.body.style.cursor = 'auto'
        }}
      >
        <sphereGeometry args={[1.05, 16, 12]} />
        <meshBasicMaterial color={base} transparent opacity={0.12} depthWrite={false} />
      </mesh>

      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation()
          onSelect(node)
        }}
        onPointerOver={(e) => {
          e.stopPropagation()
          setHovered(true)
          document.body.style.cursor = 'pointer'
        }}
        onPointerOut={() => {
          setHovered(false)
          document.body.style.cursor = 'auto'
        }}
      >
        {geometryFor(node.type)}
        <meshStandardMaterial
          color={base}
          emissive={base}
          emissiveIntensity={compromised ? 0.75 : hovered || selected ? 0.5 : 0.26}
          roughness={0.35}
          metalness={0.35}
          transparent={dimmed}
        />
      </mesh>

      <Html
        position={[0, node.type === 'firewall' ? 1.35 : 1.5, 0]}
        center
        distanceFactor={9}
        zIndexRange={[20, 0]}
        style={{ pointerEvents: 'none' }}
      >
        <div className="select-none whitespace-nowrap rounded-md border border-white/10 bg-ink-950/85 px-2 py-1 text-center backdrop-blur">
          <p className="text-[10.5px] font-semibold leading-tight text-slate-100">{node.label}</p>
          <p className="mono text-[9px] uppercase tracking-wider" style={{ color: base }}>
            {node.status} · {node.risk}
          </p>
        </div>
      </Html>
    </group>
  )
}

function Edge3D({ from, to, status }) {
  const color = EDGE_COLORS[status] || EDGE_COLORS.idle
  const lineRef = useRef()
  const active = status === 'attack' || status === 'warning'

  useFrame((_, delta) => {
    if (lineRef.current && lineRef.current.material) {
      lineRef.current.material.dashOffset -= delta * (status === 'attack' ? 0.9 : 0.35)
    }
  })

  const mid = useMemo(
    () => new THREE.Vector3((from[0] + to[0]) / 2, (from[1] + to[1]) / 2, (from[2] + to[2]) / 2),
    [from, to],
  )

  return (
    <>
      <Line
        ref={lineRef}
        points={[from, to]}
        color={color}
        lineWidth={active ? 2.2 : 1.2}
        dashed
        dashSize={active ? 0.45 : 0.22}
        gapSize={active ? 0.3 : 0.4}
        transparent
        opacity={status === 'attack' ? 0.95 : 0.7}
      />
      {status === 'attack' && (
        <mesh position={mid}>
          <sphereGeometry args={[0.13, 8, 8]} />
          <meshBasicMaterial color="#ff3b5c" />
        </mesh>
      )}
    </>
  )
}

function Packets({ edges, count = 18, paused }) {
  const refs = useRef([])
  const seeds = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        edge: i % Math.max(1, edges.length),
        t: Math.random(),
        speed: 0.18 + Math.random() * 0.35,
        reverse: i % 2 === 0,
      })),
    [edges.length, count],
  )

  useFrame((_, delta) => {
    if (paused || !edges.length) return
    seeds.forEach((s, i) => {
      const mesh = refs.current[i]
      if (!mesh) return
      s.t = (s.t + delta * s.speed) % 1
      const e = edges[s.edge]
      if (!e) return
      const k = s.reverse ? 1 - s.t : s.t
      mesh.position.set(
        e.from[0] + (e.to[0] - e.from[0]) * k,
        e.from[1] + (e.to[1] - e.from[1]) * k,
        e.from[2] + (e.to[2] - e.from[2]) * k,
      )
      const attack = e.status === 'attack'
      mesh.material.color.set(attack ? '#ff3b5c' : '#7ee7ff')
      mesh.scale.setScalar(attack ? 1.35 : 1)
    })
  })

  if (!edges.length) return null
  return (
    <group>
      {seeds.map((_, i) => (
        <mesh
          key={i}
          ref={(el) => {
            refs.current[i] = el
          }}
        >
          <sphereGeometry args={[0.075, 8, 8]} />
          <meshBasicMaterial color="#7ee7ff" />
        </mesh>
      ))}
    </group>
  )
}

function CameraReset({ controlsRef, token }) {
  const { camera } = useThree()
  const initial = useMemo(() => ({ position: new THREE.Vector3(13, 8.5, 15), target: new THREE.Vector3(0, 0, 0) }), [])
  useEffect(() => {
    if (!token) return
    camera.position.copy(initial.position)
    if (controlsRef.current) {
      controlsRef.current.target.copy(initial.target)
      controlsRef.current.update()
    }
  }, [token, camera, controlsRef, initial])
  return null
}

function Scene({ nodes, edges, selectedId, onSelect, packetCount, paused, resetToken }) {
  const controlsRef = useRef()
  const nodeMap = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n.position])), [nodes])
  const resolvedEdges = useMemo(
    () =>
      edges
        .filter((e) => nodeMap[e.source] && nodeMap[e.target])
        .map((e) => ({ from: nodeMap[e.source], to: nodeMap[e.target], status: e.status, key: `${e.source}-${e.target}` })),
    [edges, nodeMap],
  )

  return (
    <>
      <color attach="background" args={['#05070e']} />
      <fog attach="fog" args={['#05070e', 34, 66]} />
      <ambientLight intensity={0.55} />
      <directionalLight position={[10, 14, 8]} intensity={1.15} color="#cfe9ff" />
      <pointLight position={[-12, -6, -8]} intensity={0.5} color="#12b6dd" />
      <gridHelper args={[46, 46, '#0d1a2b', '#0a1322']} position={[0, -6.4, 0]} />

      {resolvedEdges.map((e) => (
        <Edge3D key={e.key} from={e.from} to={e.to} status={e.status} />
      ))}

      {nodes.map((n) => (
        <Node3D
          key={n.id}
          node={n}
          selected={selectedId === n.id}
          dimmed={Boolean(selectedId) && selectedId !== n.id}
          onSelect={onSelect}
        />
      ))}

      <Packets edges={resolvedEdges} count={packetCount} paused={paused} />

      <OrbitControls
        ref={controlsRef}
        makeDefault
        enableDamping
        dampingFactor={0.08}
        minDistance={9}
        maxDistance={44}
        maxPolarAngle={Math.PI * 0.86}
      />
      <CameraReset controlsRef={controlsRef} token={resetToken} />
    </>
  )
}

export default function NetworkScene({ nodes = [], edges = [], selectedId, onSelect, animationIntensity = 1, paused = false, resetToken = 0 }) {
  const packetCount = Math.max(6, Math.round(22 * animationIntensity))
  const handleSelect = useCallback((n) => onSelect && onSelect(n), [onSelect])

  if (!nodes.length) {
    return (
      <div className="grid h-full place-items-center text-sm text-slate-500">No topology loaded.</div>
    )
  }

  return (
    <Canvas
      dpr={[1, 1.75]}
      shadows={false}
      camera={{ position: [13, 8.5, 15], fov: 42 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      onPointerMissed={() => handleSelect(null)}
    >
      <Scene
        nodes={nodes}
        edges={edges}
        selectedId={selectedId}
        onSelect={handleSelect}
        packetCount={packetCount}
        paused={paused}
        resetToken={resetToken}
      />
    </Canvas>
  )
}
