<template>
  <div class="auth-page">
    <div class="auth-wrap">
      <section class="brand-panel">
        <p class="brand-kicker">GEWU SCHOLAR PLATFORM</p>
        <h1 class="brand-title">格物致知</h1>
        <p class="brand-desc">
          面向学术写作的检测与优化平台，提供 AIGC 检测、降重复率、降 AIGC 率三类能力，任务与结果统一管理。
        </p>
      </section>

      <section class="form-panel">
        <header class="panel-head">
          <span class="panel-tag">登录状态</span>
          <h2>未登录</h2>
          <p>请输入手机号和验证码完成登录。</p>
        </header>

        <div v-if="phoneLoginEnabled || wechatLoginEnabled" class="mode-switch">
          <button
            v-if="phoneLoginEnabled"
            type="button"
            class="mode-btn"
            :class="{ 'is-active': mode === 'phone' }"
            @click="switchMode('phone')"
          >
            手机验证码
          </button>
          <button
            v-if="wechatLoginEnabled"
            type="button"
            class="mode-btn"
            :class="{ 'is-active': mode === 'wx' }"
            @click="switchMode('wx')"
          >
            微信扫码
          </button>
        </div>

        <form v-if="mode === 'phone'" class="form-stack" @submit.prevent="login">
          <label class="field">
            <span>手机号</span>
            <input
              v-model.trim="phone"
              class="input"
              autocomplete="tel"
              placeholder="请输入 11 位手机号"
            />
          </label>

          <label class="field">
            <span>验证码</span>
            <div class="code-row">
              <input
                v-model.trim="code"
                class="input"
                style="flex: 1"
                autocomplete="one-time-code"
                placeholder="请输入验证码"
              />
              <button
                type="button"
                class="btn btn-light"
                :disabled="sending || countdown > 0"
                @click="sendCode"
              >
                {{ countdown > 0 ? `${countdown}s` : "发送验证码" }}
              </button>
            </div>
          </label>

          <button class="btn btn-primary" :disabled="loading">
            {{ loading ? "登录中..." : "登录" }}
          </button>
        </form>

        <div v-else class="wx-shell">
          <div class="wx-board">
            <div class="wx-qr">
              <img
                v-if="wxQrcodeDataUrl"
                :src="wxQrcodeDataUrl"
                alt="wx login qrcode"
                class="wx-qr-image"
              />
              <span v-else class="wx-empty">等待二维码生成</span>
            </div>
            <div class="wx-meta">
              <span class="wx-status">状态：{{ wxStatusText }}</span>
              <span class="wx-expire">剩余 {{ wxCountdown }} 秒</span>
              <button
                type="button"
                class="btn btn-light"
                @click="loadWxQrcode"
              >
                刷新二维码
              </button>
              <button
                v-if="wxMockEnabled"
                type="button"
                class="btn btn-primary"
                @click="mockWxAuthorize"
              >
                模拟扫码成功
              </button>
            </div>
          </div>
        </div>

        <p v-if="errorText" class="message message-error">{{ errorText }}</p>
        <p v-if="hintText" class="message message-success">{{ hintText }}</p>

        <div class="panel-foot">
          <RouterLink class="link-btn" :to="registerLink">去注册</RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import { getDeviceFingerprint } from "../../lib/device"
import { userHttp } from "../../lib/http"
import { resolveUserRedirect } from "../../lib/redirect"
import { setUserInfo, setUserToken } from "../../lib/session"

const route = useRoute()
const router = useRouter()

const wechatLoginEnabled = ref(false)
const wxMockEnabled = ref(false)
const phoneLoginEnabled = ref(true)

const mode = ref("phone")
const phone = ref("")
const code = ref("")
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)
const errorText = ref("")
const hintText = ref("")
const registerLink = ref("/register")

const wxKey = ref("")
const wxQrcodeDataUrl = ref("")
const wxCountdown = ref(0)
const wxStatus = ref("pending")

let timer = null
let wxCountTimer = null
let wxPollTimer = null

const wxStatusText = computed(() => {
  if (wxStatus.value === "authorized") return "已授权，正在登录"
  if (wxStatus.value === "expired") return "二维码已过期"
  return "等待扫码"
})

onMounted(async () => {
  await loadAuthOptions()
  const params = new URLSearchParams()
  const redirect = resolveUserRedirect(route.query.redirect, "")
  if (redirect) {
    params.set("redirect", redirect)
  }
  const refCode = route.query.ref
  if (typeof refCode === "string" && refCode) {
    localStorage.setItem("wuhong_referrer_code", refCode.toUpperCase())
    params.set("ref", refCode)
  }
  registerLink.value = params.toString() ? `/register?${params.toString()}` : "/register"
  if (String(route.query.mode || "") === "wx" && wechatLoginEnabled.value) {
    await switchMode("wx")
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  stopWxTimers()
})

function stopWxTimers() {
  if (wxCountTimer) {
    clearInterval(wxCountTimer)
    wxCountTimer = null
  }
  if (wxPollTimer) {
    clearInterval(wxPollTimer)
    wxPollTimer = null
  }
}

function validatePhone() {
  return /^1\d{10}$/.test(phone.value)
}

async function switchMode(nextMode) {
  if (nextMode === "wx" && !wechatLoginEnabled.value) {
    errorText.value = "当前环境未启用微信登录"
    return
  }
  mode.value = nextMode
  errorText.value = ""
  hintText.value = ""
  if (nextMode === "wx") {
    await loadWxQrcode()
  } else {
    stopWxTimers()
  }
}

async function loadAuthOptions() {
  try {
    const data = await userHttp.get("/auth/options")
    wechatLoginEnabled.value = Boolean(data.wechat_login_enabled)
    wxMockEnabled.value = Boolean(data.wx_mock_enabled)
    phoneLoginEnabled.value = data.phone_login_enabled !== false
    if (!phoneLoginEnabled.value && wechatLoginEnabled.value) {
      mode.value = "wx"
    }
  } catch {
    wechatLoginEnabled.value = false
    wxMockEnabled.value = false
    phoneLoginEnabled.value = true
  }
}

async function sendCode() {
  errorText.value = ""
  hintText.value = ""
  if (!phoneLoginEnabled.value) {
    errorText.value = "当前未开启手机号登录"
    return
  }
  if (!validatePhone()) {
    errorText.value = "手机号格式不正确"
    return
  }
  sending.value = true
  try {
    const data = await userHttp.post("/auth/send-code", { phone: phone.value })
    countdown.value = 60
    if (timer) clearInterval(timer)
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
    hintText.value = data.debug_code ? `测试验证码：${data.debug_code}` : "验证码已发送"
  } catch (error) {
    errorText.value = error.message || "发送失败"
  } finally {
    sending.value = false
  }
}

async function login() {
  errorText.value = ""
  hintText.value = ""
  if (!phoneLoginEnabled.value) {
    errorText.value = "当前未开启手机号登录"
    return
  }
  if (!validatePhone()) {
    errorText.value = "手机号格式不正确"
    return
  }
  if (!code.value) {
    errorText.value = "请输入验证码"
    return
  }
  loading.value = true
  try {
    const referrerCode = localStorage.getItem("wuhong_referrer_code") || ""
    const data = await userHttp.post("/auth/login", {
      phone: phone.value,
      code: code.value,
      referrer_code: referrerCode || undefined,
      device_fingerprint: getDeviceFingerprint(),
    })
    completeLogin(data.token, data.user)
  } catch (error) {
    errorText.value = error.message || "登录失败"
  } finally {
    loading.value = false
  }
}

async function loadWxQrcode() {
  stopWxTimers()
  wxStatus.value = "pending"
  try {
    const data = await userHttp.get("/auth/wx/qrcode")
    wxKey.value = data.key
    wxQrcodeDataUrl.value = data.qrcode_data_url
    wxCountdown.value = Number(data.expire_seconds || 120)

    wxCountTimer = setInterval(() => {
      wxCountdown.value -= 1
      if (wxCountdown.value <= 0) {
        wxCountdown.value = 0
        wxStatus.value = "expired"
        stopWxTimers()
      }
    }, 1000)
    wxPollTimer = setInterval(pollWxStatus, Number(data.poll_interval_seconds || 2) * 1000)
  } catch (error) {
    errorText.value = error.message || "获取微信二维码失败"
  }
}

async function pollWxStatus() {
  if (!wxKey.value) return
  try {
    const data = await userHttp.get(`/auth/wx/poll/${wxKey.value}`)
    wxStatus.value = data.status || "pending"
    if (wxStatus.value === "authorized" && data.token && data.user) {
      stopWxTimers()
      completeLogin(data.token, data.user)
    }
    if (wxStatus.value === "expired") {
      stopWxTimers()
    }
  } catch {
    // ignore polling failures
  }
}

async function mockWxAuthorize() {
  if (!wxKey.value) return
  try {
    await userHttp.post("/auth/wx/mock-authorize", { key: wxKey.value })
    hintText.value = "已模拟扫码授权，正在登录"
    await pollWxStatus()
  } catch (error) {
    errorText.value = error.message || "模拟扫码失败"
  }
}

function completeLogin(token, user) {
  setUserToken(token)
  setUserInfo(user)
  router.push(resolveUserRedirect(route.query.redirect, "/app/detect"))
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: clamp(18px, 4vw, 42px);
  background:
    radial-gradient(1200px 620px at 16% -8%, rgba(246, 233, 205, 0.6), transparent 72%),
    radial-gradient(900px 500px at 86% 108%, rgba(203, 226, 233, 0.5), transparent 70%),
    #f4f6f8;
  font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", "Source Han Sans SC", sans-serif;
}

.auth-wrap {
  width: min(1080px, 100%);
  margin: 0 auto;
  min-height: calc(100vh - clamp(36px, 8vw, 84px));
  background: #ffffff;
  border-radius: 24px;
  overflow: hidden;
  border: 1px solid #d9dee4;
  box-shadow: 0 20px 58px rgba(18, 33, 52, 0.08);
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
}

.brand-panel {
  padding: clamp(28px, 5vw, 62px);
  background:
    linear-gradient(158deg, rgba(19, 67, 103, 0.98), rgba(34, 98, 114, 0.9)),
    radial-gradient(circle at 88% 15%, rgba(244, 235, 216, 0.3), transparent 38%);
  color: #f4f7fb;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 18px;
}

.brand-kicker {
  margin: 0;
  letter-spacing: 0.22em;
  font-size: 11px;
  opacity: 0.72;
}

.brand-title {
  margin: 0;
  font-size: clamp(34px, 6vw, 58px);
  line-height: 1.05;
  letter-spacing: 0.08em;
  color: #fff8e6;
  font-family: "Source Han Serif SC", "Songti SC", "STSong", serif;
}

.brand-desc {
  margin: 0;
  max-width: 34ch;
  line-height: 1.9;
  font-size: 15px;
  color: rgba(245, 247, 252, 0.9);
}

.form-panel {
  padding: clamp(24px, 4vw, 40px);
  display: flex;
  flex-direction: column;
}

.panel-head h2 {
  margin: 8px 0 6px;
  font-size: 30px;
  color: #1d2a36;
  font-family: "Source Han Serif SC", "Songti SC", "STSong", serif;
}

.panel-head p {
  margin: 0;
  color: #5f6d79;
  font-size: 14px;
}

.panel-tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: #14574b;
  background: #e5f3ef;
}

.mode-switch {
  margin-top: 18px;
  display: flex;
  gap: 8px;
}

.mode-btn {
  flex: 1;
  border: 1px solid #d4dde6;
  background: #f7fafc;
  color: #3f4f5e;
  border-radius: 12px;
  height: 38px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-btn.is-active {
  background: #113f58;
  color: #ffffff;
  border-color: #113f58;
}

.form-stack {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: #4f5d69;
}

.input {
  height: 44px;
  border-radius: 12px;
  border: 1px solid #cfd9e2;
  padding: 0 14px;
  font-size: 14px;
  color: #22313e;
  background: #ffffff;
}

.input:focus {
  outline: none;
  border-color: #2f688a;
  box-shadow: 0 0 0 3px rgba(47, 104, 138, 0.14);
}

.code-row {
  display: flex;
  gap: 10px;
}

.btn {
  border: none;
  border-radius: 12px;
  height: 44px;
  padding: 0 16px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(132deg, #135278, #1b6b80);
  color: #ffffff;
  width: 100%;
}

.btn-light {
  background: #edf3f7;
  color: #2f4152;
}

.wx-shell {
  margin-top: 18px;
}

.wx-board {
  border: 1px solid #d6e0e8;
  border-radius: 14px;
  padding: 14px;
  background: #f9fbfd;
}

.wx-qr {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 12px;
  border: 1px dashed #becad6;
  display: grid;
  place-items: center;
  background: #ffffff;
}

.wx-qr-image {
  width: min(210px, 100%);
  height: auto;
}

.wx-empty {
  color: #7b8997;
  font-size: 13px;
}

.wx-meta {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.wx-status,
.wx-expire {
  font-size: 12px;
  color: #4f6070;
}

.message {
  margin: 12px 0 0;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
}

.message-error {
  border: 1px solid #f0d3cd;
  background: #fff6f4;
  color: #9f3f34;
}

.message-success {
  border: 1px solid #cde8dc;
  background: #f2fbf6;
  color: #17674f;
}

.panel-foot {
  margin-top: 16px;
}

.link-btn {
  display: inline-block;
  color: #205d80;
  text-decoration: none;
  font-size: 14px;
  border-bottom: 1px solid rgba(32, 93, 128, 0.35);
  padding-bottom: 2px;
}

@media (max-width: 960px) {
  .auth-wrap {
    grid-template-columns: 1fr;
  }

  .brand-panel {
    min-height: 260px;
  }
}
</style>
