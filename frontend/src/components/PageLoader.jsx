import React from 'react'
import { Spinner } from './ui'

export default function PageLoader({ label = 'Loading module' }) {
  return (
    <div className="flex h-[60vh] flex-col items-center justify-center gap-3 text-slate-400">
      <Spinner size={26} className="text-cyber-400" />
      <p className="label-caps">{label}</p>
    </div>
  )
}
