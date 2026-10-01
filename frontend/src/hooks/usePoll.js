import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Lightweight polling hook with manual refresh and error capture.
 */
export default function usePoll(fn, interval = 4000, { enabled = true, immediate = true } = {}) {
  const fnRef = useRef(fn)
  fnRef.current = fn
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(immediate && enabled)
  const [updatedAt, setUpdatedAt] = useState(null)
  const tickRef = useRef(0)

  const tick = useCallback(async () => {
    try {
      const result = await fnRef.current()
      setData(result)
      setError(null)
      setUpdatedAt(Date.now())
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  const refresh = useCallback(() => {
    tickRef.current += 1
    return tick()
  }, [tick])

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return undefined
    }
    let cancelled = false
    const run = async () => {
      if (cancelled) return
      await tick()
    }
    run()
    const id = setInterval(run, interval)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [interval, enabled, tick])

  return { data, error, loading, updatedAt, refresh }
}
