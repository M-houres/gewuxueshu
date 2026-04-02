import axios from "axios"

import {
  clearAdminSession,
  clearUserSession,
  getAdminToken,
  getUserToken,
} from "./session"

function resolveBaseURL() {
  const explicit = import.meta.env.VITE_API_BASE_URL
  if (explicit) {
    return explicit
  }
  if (typeof window !== "undefined") {
    const { hostname, port } = window.location
    const isLocalPreview =
      (hostname === "127.0.0.1" || hostname === "localhost") &&
      /^517\d$/.test(port)
    if (isLocalPreview) {
      return "http://127.0.0.1:8100/api/v1"
    }
  }
  return "/api/v1"
}

const baseURL = resolveBaseURL()

function unwrapResponse(response) {
  const responseType = response?.config?.responseType
  if (responseType === "blob" || responseType === "arraybuffer") {
    return response
  }
  const payload = response.data
  if (payload && typeof payload.code === "number") {
    if (payload.code !== 0) {
      const err = new Error(payload.message || "请求失败")
      err.code = payload.code
      throw err
    }
    return payload.data
  }
  return payload
}

async function normalizeBlobError(data) {
  if (typeof Blob === "undefined" || !(data instanceof Blob)) {
    return null
  }
  const rawText = await data.text()
  const text = String(rawText || "").trim()
  if (!text) {
    return null
  }
  try {
    const payload = JSON.parse(text)
    if (payload && typeof payload === "object" && payload.message) {
      return {
        message: payload.message,
        code: payload.code,
      }
    }
  } catch {}
  return { message: text }
}

async function normalizeError(error) {
  const blobError = await normalizeBlobError(error?.response?.data)
  if (blobError?.message) {
    const err = new Error(blobError.message)
    err.code = blobError.code
    return Promise.reject(err)
  }
  if (error?.response?.data?.message) {
    const err = new Error(error.response.data.message)
    err.code = error.response.data.code
    return Promise.reject(err)
  }
  return Promise.reject(error)
}

export const userHttp = axios.create({ baseURL, timeout: 20000 })
userHttp.interceptors.request.use((config) => {
  config.headers["X-Client-Source"] = "web"
  const token = getUserToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
userHttp.interceptors.response.use(
  (resp) => unwrapResponse(resp),
  async (error) => {
    if (error?.response?.status === 401) {
      const hadToken = Boolean(getUserToken())
      clearUserSession()
      if (hadToken) {
        const redirect = encodeURIComponent(`${location.pathname}${location.search}`)
        location.href = `/login?redirect=${redirect}`
      }
    }
    return normalizeError(error)
  }
)

export const adminHttp = axios.create({ baseURL, timeout: 20000 })
adminHttp.interceptors.request.use((config) => {
  config.headers["X-Client-Source"] = "web"
  const token = getAdminToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
adminHttp.interceptors.response.use(
  (resp) => unwrapResponse(resp),
  async (error) => {
    if (error?.response?.status === 401) {
      const hadToken = Boolean(getAdminToken())
      clearAdminSession()
      if (hadToken) {
        const redirect = encodeURIComponent(`${location.pathname}${location.search}`)
        location.href = `/admin/login?redirect=${redirect}`
      }
    }
    return normalizeError(error)
  }
)
