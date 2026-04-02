const USER_ROUTE_PREFIX = "/app/"
const ADMIN_ROUTE_PREFIX = "/admin/"
const USER_ROUTE_ALIASES = new Set([
  "/",
  "/detect",
  "/dedup",
  "/rewrite",
  "/history",
  "/buy",
  "/credits",
  "/profile",
  "/referral",
])
const ADMIN_ROUTE_ALIASES = new Set(["/admin"])

function splitRedirectTarget(rawRedirect) {
  if (typeof rawRedirect !== "string" || !rawRedirect.startsWith("/")) {
    return { path: "", suffix: "" }
  }
  const match = rawRedirect.match(/^([^?#]*)(.*)$/)
  return {
    path: match?.[1] || rawRedirect,
    suffix: match?.[2] || "",
  }
}

export function resolveUserRedirect(rawRedirect, fallback = "/app/detect") {
  const { path, suffix } = splitRedirectTarget(rawRedirect)
  if (!path) {
    return fallback
  }
  if (path.startsWith(USER_ROUTE_PREFIX) || USER_ROUTE_ALIASES.has(path)) {
    return `${path}${suffix}`
  }
  return fallback
}

export function resolveAdminRedirect(rawRedirect, fallback = "/admin/dashboard") {
  const { path, suffix } = splitRedirectTarget(rawRedirect)
  if (!path) {
    return fallback
  }
  if (path.startsWith(ADMIN_ROUTE_PREFIX) || ADMIN_ROUTE_ALIASES.has(path)) {
    return `${path}${suffix}`
  }
  return fallback
}
