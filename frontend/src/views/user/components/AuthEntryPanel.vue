<template>
  <div class="auth-page">
    <div class="auth-layout">
      <section class="brand-area">
        <p class="brand-mark">学术写作智能工作台</p>
        <h1 class="brand-title">格物致知</h1>
        <p class="brand-intro">
          面向论文场景的实用平台，支持仿知网 AIGC 检测、降重复率、降 AIGC 率，任务和积分统一沉淀到个人中心。
        </p>
        <ul class="brand-points">
          <li>手机号验证码登录与注册合一</li>
          <li>微信扫码与手机号入口并行可用</li>
          <li>登录后直接进入统一工作台</li>
        </ul>
      </section>

      <section class="entry-area">
        <header class="entry-header">
          <p class="entry-kicker">{{ entryKicker }}</p>
          <h2>{{ entryTitle }}</h2>
          <p>输入手机号和验证码继续。未注册手机号会自动创建账号并直接登录。</p>
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

        <form v-if="mode === 'phone'" class="entry-form" @submit.prevent="submitPhoneAuth">
          <label class="field">
            <span>手机号</span>
            <input
              v-model.trim="phone"
              class="field-input"
              autocomplete="tel"
              placeholder="请输入 11 位手机号"
            />
          </label>

          <label class="field">
            <span>验证码</span>
            <div class="code-row">
              <input
                v-model.trim="code"
                class="field-input"
                style="flex: 1"
                autocomplete="one-time-code"
                placeholder="请输入验证码"
              />
              <button
                type="button"
                class="text-btn"
                :disabled="sending || countdown > 0"
                @click="sendCode"
              >
                {{ countdown > 0 ? `${countdown}s` : "发送验证码" }}
              </button>
            </div>
          </label>

          <label class="policy-line">
            <input v-model="agreedPolicy" type="checkbox" />
            <span>我已阅读并同意服务协议与隐私政策</span>
          </label>

          <button class="primary-btn" :disabled="loading">
            {{ loading ? "处理中..." : primaryButtonText }}
          </button>
        </form>

        <div v-else class="wx-shell">
          <div class="wx-qr">
            <img v-if="wxQrcodeDataUrl" :src="wxQrcodeDataUrl" alt="微信扫码登录二维码" class="wx-qr-image" />
            <span v-else class="wx-empty">二维码生成中</span>
          </div>
          <div class="wx-meta">
            <span>{{ wxStatusText }}</span>
            <span>剩余 {{ wxCountdown }} 秒</span>
          </div>
          <div class="wx-actions">
            <button type="button" class="secondary-btn" @click="loadWxQrcode">刷新二维码</button>
            <button v-if="wxMockEnabled" type="button" class="primary-btn" @click="mockWxAuthorize">模拟扫码成功</button>
          </div>
        </div>

        <p v-if="errorText" class="notice notice-error">{{ errorText }}</p>
        <p v-if="hintText" class="notice notice-success">{{ hintText }}</p>

        <div class="entry-footer">
          <RouterLink class="switch-link" :to="alternateEntryLink">{{ alternateEntryText }}</RouterLink>
          <button type="button" class="ghost-btn" @click="enterGuest">先体验</button>
        </div>

        <p class="security-tip">
          验证码 5 分钟有效，连续输错会短暂锁定账号
          <template v-if="newUserCredits !== null">，新用户初始积分 {{ newUserCredits }}</template>。
        </p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import { getDeviceFingerprint } from "../../../lib/device"
import { userHttp } from "../../../lib/http"
import { resolveUserRedirect } from "../../../lib/redirect"
import { setUserInfo, setUserToken } from "../../../lib/session"

const props = defineProps({
  entryType: {
    type: String,
    default: "login",
  },
})

const route = useRoute()
const router = useRouter()

const wechatLoginEnabled = ref(false)
const wxMockEnabled = ref(false)
const phoneLoginEnabled = ref(true)
const newUserCredits = ref(null)

const mode = ref("phone")
const phone = ref("")
const code = ref("")
const agreedPolicy = ref(true)
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)
const errorText = ref("")
const hintText = ref("")
const alternateEntryLink = ref("/register")
const referrerCode = ref("")

const wxKey = ref("")
const wxQrcodeDataUrl = ref("")
const wxCountdown = ref(0)
const wxStatus = ref("pending")

let smsCountdownTimer = null
let wxCountTimer = null
let wxPollTimer = null

const isRegisterPage = computed(() => props.entryType === "register")
const entryKicker = computed(() => (isRegisterPage.value ? "新用户入口" : "账号入口"))
const entryTitle = computed(() => (isRegisterPage.value ? "注册并进入工作台" : "登录进入工作台"))
const primaryButtonText = computed(() => (isRegisterPage.value ? "注册并进入工作台" : "继续"))
const alternateEntryText = computed(() => (isRegisterPage.value ? "已有账号，去登录" : "新用户注册"))
const wxStatusText = computed(() => {
  if (wxStatus.value === "authorized") return "已授权，正在登录"
  if (wxStatus.value === "expired") return "二维码已过期"
  return "等待扫码授权"
})

onMounted(async () => {
  await loadAuthOptions()
  syncRouteParams()
  if (String(route.query.mode || "") === "wx" && wechatLoginEnabled.value) {
    await switchMode("wx")
  }
})

onUnmounted(() => {
  stopSmsCountdown()
  stopWxTimers()
})

function syncRouteParams() {
  const params = new URLSearchParams()
  const redirect = resolveUserRedirect(route.query.redirect, "")
  if (redirect) {
    params.set("redirect", redirect)
  }

  const queryRef = route.query.ref
  if (typeof queryRef === "string" && queryRef.trim()) {
    referrerCode.value = queryRef.trim().toUpperCase()
    localStorage.setItem("wuhong_referrer_code", referrerCode.value)
    params.set("ref", referrerCode.value)
  } else {
    const cachedRef = localStorage.getItem("wuhong_referrer_code")
    referrerCode.value = cachedRef ? cachedRef.toUpperCase() : ""
    if (referrerCode.value) {
      params.set("ref", referrerCode.value)
    }
  }

  const targetPath = isRegisterPage.value ? "/login" : "/register"
  alternateEntryLink.value = params.toString() ? `${targetPath}?${params.toString()}` : targetPath
}

function stopSmsCountdown() {
  if (smsCountdownTimer) {
    clearInterval(smsCountdownTimer)
    smsCountdownTimer = null
  }
}

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

async function loadAuthOptions() {
  try {
    const data = await userHttp.get("/auth/options")
    wechatLoginEnabled.value = Boolean(data.wechat_login_enabled)
    wxMockEnabled.value = Boolean(data.wx_mock_enabled)
    phoneLoginEnabled.value = data.phone_login_enabled !== false
    if (typeof data.new_user_initial_credits === "number") {
      newUserCredits.value = data.new_user_initial_credits
    }
    if (!phoneLoginEnabled.value && wechatLoginEnabled.value) {
      mode.value = "wx"
    }
  } catch {
    wechatLoginEnabled.value = false
    wxMockEnabled.value = false
    phoneLoginEnabled.value = true
    newUserCredits.value = null
  }
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
    return
  }
  stopWxTimers()
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
    await userHttp.post("/auth/send-code", { phone: phone.value })
    countdown.value = 60
    stopSmsCountdown()
    smsCountdownTimer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) {
        countdown.value = 0
        stopSmsCountdown()
      }
    }, 1000)
    hintText.value = "验证码已发送，请注意查收短信"
  } catch (error) {
    errorText.value = error.message || "发送验证码失败"
  } finally {
    sending.value = false
  }
}

async function submitPhoneAuth() {
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
  if (!agreedPolicy.value) {
    errorText.value = "请先同意服务协议与隐私政策"
    return
  }
  loading.value = true
  try {
    const data = await userHttp.post("/auth/login", {
      phone: phone.value,
      code: code.value,
      referrer_code: referrerCode.value || undefined,
      device_fingerprint: getDeviceFingerprint(),
    })
    completeLogin(data.token, data.user)
  } catch (error) {
    errorText.value = error.message || "登录失败，请稍后重试"
  } finally {
    loading.value = false
  }
}

async function loadWxQrcode() {
  stopWxTimers()
  wxStatus.value = "pending"
  errorText.value = ""
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
      return
    }
    if (wxStatus.value === "expired") {
      stopWxTimers()
    }
  } catch {
    // Keep polling in case of transient failures.
  }
}

async function mockWxAuthorize() {
  if (!wxKey.value) return
  try {
    await userHttp.post("/auth/wx/mock-authorize", { key: wxKey.value })
    hintText.value = "已模拟扫码授权，正在处理登录"
    await pollWxStatus()
  } catch (error) {
    errorText.value = error.message || "模拟扫码失败"
  }
}

function completeLogin(token, user) {
  setUserToken(token)
  setUserInfo(user)
  localStorage.removeItem("wuhong_referrer_code")
  router.push(resolveUserRedirect(route.query.redirect, "/app/detect"))
}

function enterGuest() {
  router.push("/app/detect")
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: clamp(16px, 3.4vw, 36px);
  background:
    radial-gradient(680px 420px at 0% 8%, rgba(215, 236, 247, 0.74), transparent 70%),
    radial-gradient(760px 480px at 100% 100%, rgba(246, 228, 203, 0.48), transparent 72%),
    #f4f6f7;
  font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.auth-layout {
  width: min(1060px, 100%);
  margin: 0 auto;
  background: #ffffff;
  border-radius: 24px;
  border: 1px solid #d8e0e4;
  overflow: hidden;
  display: grid;
  grid-template-columns: 1.12fr 0.88fr;
  box-shadow: 0 20px 52px rgba(34, 53, 69, 0.12);
}

.brand-area {
  padding: clamp(30px, 4vw, 46px);
  background:
    radial-gradient(circle at 78% 16%, rgba(255, 224, 180, 0.2), transparent 42%),
    linear-gradient(153deg, #153a53 0%, #1e4f63 55%, #266270 100%);
  color: #eef5f9;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 16px;
}

.brand-mark {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.14em;
  opacity: 0.8;
}

.brand-title {
  margin: 0;
  font-size: clamp(36px, 5.4vw, 54px);
  line-height: 1.03;
  letter-spacing: 0.06em;
  color: #fff6e8;
  font-family: "Source Han Serif SC", "Songti SC", "STSong", serif;
}

.brand-intro {
  margin: 0;
  max-width: 33ch;
  font-size: 14px;
  line-height: 1.85;
  color: rgba(237, 245, 249, 0.92);
}

.brand-points {
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
  font-size: 13px;
  color: rgba(245, 250, 252, 0.92);
}

.brand-points li {
  position: relative;
  padding-left: 18px;
}

.brand-points li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 7px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 236, 205, 0.95);
}

.entry-area {
  padding: clamp(22px, 3.2vw, 36px);
  background: linear-gradient(180deg, #fdfefe 0%, #f6f8f9 100%);
}

.entry-header {
  margin-bottom: 14px;
}

.entry-kicker {
  margin: 0;
  color: #2d7081;
  font-size: 12px;
  letter-spacing: 0.08em;
}

.entry-header h2 {
  margin: 6px 0 8px;
  color: #1c2f3a;
  font-size: 30px;
  line-height: 1.14;
  font-family: "Source Han Serif SC", "Songti SC", "STSong", serif;
}

.entry-header p {
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: #596c79;
}

.mode-switch {
  margin-bottom: 14px;
  display: flex;
  gap: 9px;
}

.mode-btn {
  flex: 1;
  height: 38px;
  border-radius: 11px;
  border: 1px solid #ccd7de;
  background: #edf2f5;
  color: #3f5462;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-btn.is-active {
  border-color: #1f5d74;
  background: #1f5d74;
  color: #ffffff;
}

.entry-form {
  display: grid;
  gap: 12px;
}

.field {
  display: grid;
  gap: 7px;
}

.field span {
  font-size: 13px;
  color: #405666;
  font-weight: 600;
}

.field-input {
  height: 44px;
  border-radius: 12px;
  border: 1px solid #c9d6df;
  background: #ffffff;
  padding: 0 13px;
  color: #1f3443;
  font-size: 14px;
}

.field-input:focus {
  outline: none;
  border-color: #2f667e;
  box-shadow: 0 0 0 3px rgba(47, 102, 126, 0.15);
}

.code-row {
  display: flex;
  gap: 8px;
}

.text-btn,
.secondary-btn,
.primary-btn,
.ghost-btn {
  height: 44px;
  border-radius: 12px;
  border: none;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.text-btn {
  min-width: 112px;
  border: 1px solid #ccd7de;
  background: #f0f4f7;
  color: #3f5462;
}

.text-btn:disabled,
.secondary-btn:disabled,
.primary-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.policy-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #5c7080;
}

.policy-line input {
  width: 15px;
  height: 15px;
}

.primary-btn {
  width: 100%;
  color: #ffffff;
  background: linear-gradient(128deg, #1c4e69 0%, #27677a 100%);
}

.secondary-btn {
  background: #eef3f6;
  color: #3f5566;
}

.wx-shell {
  display: grid;
  gap: 11px;
}

.wx-qr {
  aspect-ratio: 1 / 1;
  border: 1px dashed #beced8;
  border-radius: 14px;
  background: #ffffff;
  display: grid;
  place-items: center;
  padding: 12px;
}

.wx-qr-image {
  width: min(214px, 100%);
  height: auto;
}

.wx-empty {
  color: #758a98;
  font-size: 13px;
}

.wx-meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #4f6675;
}

.wx-actions {
  display: flex;
  gap: 9px;
}

.wx-actions .secondary-btn,
.wx-actions .primary-btn {
  flex: 1;
}

.notice {
  margin: 12px 0 0;
  border-radius: 12px;
  padding: 9px 11px;
  font-size: 13px;
}

.notice-error {
  border: 1px solid #f0d3cd;
  background: #fff5f3;
  color: #a74238;
}

.notice-success {
  border: 1px solid #cbe8da;
  background: #f1fbf6;
  color: #19664a;
}

.entry-footer {
  margin-top: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.switch-link {
  color: #1f6078;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
}

.switch-link:hover {
  text-decoration: underline;
}

.ghost-btn {
  height: 34px;
  border: 1px solid #d4dee4;
  background: #f7fafc;
  color: #5d707f;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 500;
}

.security-tip {
  margin: 10px 0 0;
  color: #6f808c;
  font-size: 12px;
  line-height: 1.7;
}

@media (max-width: 960px) {
  .auth-layout {
    grid-template-columns: 1fr;
  }

  .brand-area {
    min-height: 240px;
  }
}
</style>
