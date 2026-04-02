import { getUserToken } from "./session"

export function ensureUserLogin(router, route, fallback = "/app/detect") {
  if (getUserToken()) {
    return true
  }
  const redirect = encodeURIComponent(route?.fullPath || fallback)
  router.push(`/login?redirect=${redirect}`)
  return false
}

