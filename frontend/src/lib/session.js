const USER_TOKEN_KEY = "wuhong_user_token"
const ADMIN_TOKEN_KEY = "wuhong_admin_token"
const USER_INFO_KEY = "wuhong_user_info"
const ADMIN_INFO_KEY = "wuhong_admin_info"

export function getUserToken() {
  return localStorage.getItem(USER_TOKEN_KEY) || ""
}

export function setUserToken(token) {
  if (!token) {
    localStorage.removeItem(USER_TOKEN_KEY)
    return
  }
  localStorage.setItem(USER_TOKEN_KEY, token)
}

export function clearUserSession() {
  localStorage.removeItem(USER_TOKEN_KEY)
  localStorage.removeItem(USER_INFO_KEY)
}

export function getAdminToken() {
  return localStorage.getItem(ADMIN_TOKEN_KEY) || ""
}

export function setAdminToken(token) {
  if (!token) {
    localStorage.removeItem(ADMIN_TOKEN_KEY)
    return
  }
  localStorage.setItem(ADMIN_TOKEN_KEY, token)
}

export function clearAdminSession() {
  localStorage.removeItem(ADMIN_TOKEN_KEY)
  localStorage.removeItem(ADMIN_INFO_KEY)
}

export function setUserInfo(user) {
  if (!user) {
    localStorage.removeItem(USER_INFO_KEY)
    return
  }
  localStorage.setItem(USER_INFO_KEY, JSON.stringify(user))
}

export function getUserInfo() {
  const raw = localStorage.getItem(USER_INFO_KEY)
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function setAdminInfo(admin) {
  if (!admin) {
    localStorage.removeItem(ADMIN_INFO_KEY)
    return
  }
  localStorage.setItem(ADMIN_INFO_KEY, JSON.stringify(admin))
}

export function getAdminInfo() {
  const raw = localStorage.getItem(ADMIN_INFO_KEY)
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}
