const DEVICE_FINGERPRINT_KEY = "wuhong_device_fingerprint"

function createFingerprint() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }
  const rand = Math.random().toString(16).slice(2)
  return `fp-${Date.now().toString(16)}-${rand}`
}

export function getDeviceFingerprint() {
  const existing = localStorage.getItem(DEVICE_FINGERPRINT_KEY)
  if (existing) {
    return existing
  }
  const next = createFingerprint()
  localStorage.setItem(DEVICE_FINGERPRINT_KEY, next)
  return next
}
