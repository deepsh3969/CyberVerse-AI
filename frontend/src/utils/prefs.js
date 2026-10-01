export const PREFS_KEY = 'cyberverse.prefs'

export const DEFAULT_PREFS = {
  animationIntensity: 1,
  sound: false,
  theme: 'command',
  refreshInterval: 4000,
  demoMode: true,
}

export function loadPrefs() {
  try {
    const raw = window.localStorage.getItem(PREFS_KEY)
    if (!raw) return { ...DEFAULT_PREFS }
    return { ...DEFAULT_PREFS, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULT_PREFS }
  }
}

export function savePrefs(prefs) {
  try {
    window.localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  } catch {
    /* storage unavailable - prefs stay in memory */
  }
}

/** Short, non-intrusive alert tone generated with WebAudio (no assets needed). */
export function playTone(kind = 'alert') {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return
    const ctx = new Ctx()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.value = kind === 'success' ? 660 : kind === 'warn' ? 520 : 380
    gain.gain.setValueAtTime(0.0001, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.06, ctx.currentTime + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.45)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.5)
    setTimeout(() => ctx.close(), 900)
  } catch {
    /* audio unsupported */
  }
}
