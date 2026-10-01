import '@testing-library/jest-dom'
import { vi } from 'vitest'

// jsdom lacks these browser APIs used by three.js / recharts.
window.HTMLCanvasElement.prototype.getContext = vi.fn(() => null)
window.scrollTo = vi.fn()

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = window.ResizeObserver || ResizeObserverStub
global.ResizeObserver = global.ResizeObserver || ResizeObserverStub

window.matchMedia =
  window.matchMedia ||
  (() => ({
    matches: false,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
  }))
