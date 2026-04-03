<template>
  <div class="cnki-auth-page">
    <div class="cnki-auth-shell">
      <section class="cnki-auth-left">
        <header class="cnki-auth-brand">
          <div class="cnki-auth-logo">格</div>
          <div>
            <p class="cnki-auth-brand-top">格物致知</p>
            <h1 class="cnki-auth-brand-title">格物学术</h1>
          </div>
        </header>

        <p class="cnki-auth-subtitle">论文场景智能服务平台</p>
        <p class="cnki-auth-lead">
          聚焦仿知网检测、降重复率与降 AIGC 率，统一账号体系与积分体系，减少重复操作。
        </p>

        <ul class="cnki-auth-service-list">
          <li v-for="item in serviceHighlights" :key="item.title" class="cnki-auth-service-item">
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </li>
        </ul>

        <footer class="cnki-auth-note">
          <p>任务记录与积分流水统一归档至个人中心，便于后续复核与下载。</p>
          <p v-if="newUserCredits !== null">
            新用户注册默认赠送 <strong>{{ newUserCredits }} 积分</strong>（后台可配置）。
          </p>
        </footer>
      </section>

      <section class="cnki-auth-right">
        <article class="cnki-auth-card">
          <header class="cnki-auth-card-head">
            <p class="cnki-auth-kicker">{{ entryKicker }}</p>
            <h2>{{ entryTitle }}</h2>
            <p>输入手机号与验证码即可继续，未注册手机号会自动创建账号并登录。</p>
          </header>

          <div v-if="phoneLoginEnabled || wechatLoginEnabled" class="cnki-auth-mode-switch">
            <button
              v-if="phoneLoginEnabled"
              type="button"
              class="cnki-auth-mode-btn"
              :class="{ 'is-active': mode === 'phone' }"
              @click="switchMode('phone')"
            >
              手机验证码登录
            </button>
            <button
              v-if="wechatLoginEnabled"
              type="button"
              class="cnki-auth-mode-btn"
              :class="{ 'is-active': mode === 'wx' }"
              @click="switchMode('wx')"
            >
              微信扫码登录
            </button>
          </div>

          <form v-if="mode === 'phone'" class="cnki-auth-form" @submit.prevent="submitPhoneAuth">
            <label class="cnki-auth-field">
              <span>手机号</span>
              <input
                v-model.trim="phone"
                class="cnki-auth-input"
                autocomplete="tel"
                placeholder="请输入 11 位手机号"
              />
            </label>

            <label class="cnki-auth-field">
              <span>验证码</span>
              <div class="cnki-auth-code-row">
                <input
                  v-model.trim="code"
                  class="cnki-auth-input"
                  style="flex: 1"
                  autocomplete="one-time-code"
                  placeholder="请输入验证码"
                />
                <button
                  type="button"
                  class="cnki-auth-code-btn"
                  :disabled="sending || countdown > 0"
                  @click="sendCode"
                >
                  {{ countdown > 0 ? `${countdown}s` : "发送验证码" }}
                </button>
              </div>
            </label>

            <label class="cnki-auth-policy">
              <input v-model="agreedPolicy" type="checkbox" />
              <span>我已阅读并同意服务协议与隐私政策</span>
            </label>

            <button class="cnki-auth-submit" :disabled="loading">
              {{ loading ? "处理中..." : primaryButtonText }}
            </button>
          </form>

          <div v-else class="cnki-auth-wx-shell">
            <div class="cnki-auth-wx-qr">
              <img v-if="wxQrcodeDataUrl" :src="wxQrcodeDataUrl" alt="微信扫码登录二维码" class="cnki-auth-wx-qr-image" />
              <span v-else class="cnki-auth-wx-empty">二维码生成中</span>
            </div>
            <div class="cnki-auth-wx-meta">
              <span>{{ wxStatusText }}</span>
              <span>剩余 {{ wxCountdown }} 秒</span>
            </div>
            <div class="cnki-auth-wx-actions">
              <button type="button" class="cnki-auth-secondary" @click="loadWxQrcode">刷新二维码</button>
              <button v-if="wxMockEnabled" type="button" class="cnki-auth-submit" @click="mockWxAuthorize">
                模拟扫码成功
              </button>
            </div>
          </div>

          <p v-if="errorText" class="cnki-auth-notice cnki-auth-notice--error">{{ errorText }}</p>
          <p v-if="hintText" class="cnki-auth-notice cnki-auth-notice--success">{{ hintText }}</p>

          <div class="cnki-auth-footer">
            <RouterLink class="cnki-auth-switch-link" :to="alternateEntryLink">{{ alternateEntryText }}</RouterLink>
            <button type="button" class="cnki-auth-ghost" @click="enterGuest">游客先浏览</button>
          </div>

          <p class="cnki-auth-security-tip">验证码 5 分钟内有效，连续输入错误会短暂锁定账号。</p>
        </article>
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

const serviceHighlights = [
  {
    title: "仿知网 AIGC 检测",
    desc: "按目标平台策略输出风险区段与检测报告，适合提交前自查。",
  },
  {
    title: "降重复率",
    desc: "结合语义重构降低重复表达，兼顾论点连贯性与阅读流畅度。",
  },
  {
    title: "降 AIGC 率",
    desc: "在保留结构与观点前提下优化文本表达，降低 AI 痕迹感。",
  },
]

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
const entryKicker = computed(() => (isRegisterPage.value ? "新用户注册" : "账号登录"))
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
    // Keep polling for transient failures.
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
.cnki-auth-page {
  min-height: 100vh;
  padding: clamp(16px, 3.4vw, 34px);
  background:
    radial-gradient(860px 420px at 8% 0%, rgba(43, 109, 201, 0.12), transparent 72%),
    radial-gradient(760px 500px at 96% 100%, rgba(23, 132, 201, 0.08), transparent 70%),
    linear-gradient(180deg, #f5f8fd 0%, #edf3fb 100%);
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
}

.cnki-auth-shell {
  width: min(1180px, 100%);
  min-height: min(760px, calc(100vh - 68px));
  margin: 0 auto;
  border-radius: 26px;
  border: 1px solid rgba(64, 116, 187, 0.22);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 251, 255, 0.94));
  box-shadow: 0 24px 56px rgba(28, 53, 94, 0.12);
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(380px, 0.88fr);
  overflow: hidden;
}

.cnki-auth-left {
  position: relative;
  padding: clamp(28px, 4vw, 46px);
  display: grid;
  align-content: start;
  gap: 18px;
  background:
    radial-gradient(circle at 10% 8%, rgba(67, 125, 211, 0.11), transparent 24%),
    linear-gradient(180deg, rgba(245, 250, 255, 0.98), rgba(240, 247, 255, 0.95));
}

.cnki-auth-left::after {
  content: "";
  position: absolute;
  right: 28px;
  top: 24px;
  width: 120px;
  height: 120px;
  border-radius: 18px;
  border: 1px dashed rgba(63, 113, 178, 0.24);
  background: rgba(255, 255, 255, 0.3);
  transform: rotate(10deg);
  pointer-events: none;
}

.cnki-auth-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cnki-auth-logo {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 19px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #1e5cb2 0%, #2f7ec9 100%);
  box-shadow: 0 10px 20px rgba(34, 87, 159, 0.22);
}

.cnki-auth-brand-top {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.22em;
  color: #6c83a6;
}

.cnki-auth-brand-title {
  margin: 6px 0 0;
  font-size: clamp(35px, 4.3vw, 52px);
  line-height: 1.04;
  color: #1c3f7f;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.cnki-auth-subtitle {
  margin: 6px 0 0;
  font-size: 16px;
  font-weight: 700;
  color: #2d5696;
}

.cnki-auth-lead {
  margin: 0;
  max-width: 48ch;
  font-size: 14px;
  line-height: 1.85;
  color: #4c6689;
}

.cnki-auth-service-list {
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 12px;
}

.cnki-auth-service-item {
  padding: 14px 15px 15px;
  border-radius: 16px;
  border: 1px solid rgba(72, 119, 187, 0.2);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(244, 250, 255, 0.86)),
    linear-gradient(135deg, rgba(43, 109, 201, 0.05), transparent 62%);
}

.cnki-auth-service-item h3 {
  margin: 0;
  font-size: 17px;
  color: #285293;
  font-weight: 800;
}

.cnki-auth-service-item p {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: #516d8f;
}

.cnki-auth-note {
  margin-top: 4px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(79, 123, 183, 0.2);
  background: rgba(255, 255, 255, 0.78);
  display: grid;
  gap: 4px;
}

.cnki-auth-note p {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
  color: #617899;
}

.cnki-auth-note strong {
  color: #1f569f;
}

.cnki-auth-right {
  padding: clamp(24px, 3.1vw, 36px);
  border-left: 1px solid rgba(72, 116, 177, 0.2);
  background: linear-gradient(180deg, rgba(252, 254, 255, 0.98), rgba(246, 250, 255, 0.96));
}

.cnki-auth-card {
  min-height: 100%;
  border-radius: 22px;
  border: 1px solid rgba(93, 131, 182, 0.2);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 252, 255, 0.92)),
    linear-gradient(135deg, rgba(43, 109, 201, 0.04), transparent 58%);
  padding: 24px 22px;
  box-shadow: 0 14px 34px rgba(30, 63, 106, 0.1);
  display: grid;
  align-content: start;
  gap: 14px;
}

.cnki-auth-card-head {
  display: grid;
  gap: 8px;
}

.cnki-auth-kicker {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.13em;
  color: #6382ad;
  font-weight: 700;
}

.cnki-auth-card-head h2 {
  margin: 0;
  font-size: 31px;
  line-height: 1.1;
  color: #1d457f;
  font-weight: 800;
}

.cnki-auth-card-head p {
  margin: 0;
  font-size: 13px;
  line-height: 1.75;
  color: #5c7698;
}

.cnki-auth-mode-switch {
  display: flex;
  gap: 10px;
}

.cnki-auth-mode-btn {
  flex: 1;
  height: 40px;
  border-radius: 11px;
  border: 1px solid rgba(106, 133, 170, 0.42);
  background: rgba(241, 247, 255, 0.92);
  color: #44638f;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.cnki-auth-mode-btn.is-active {
  border-color: rgba(45, 98, 175, 0.72);
  background: linear-gradient(135deg, #2a67bf, #2f83c9);
  color: #fff;
  box-shadow: 0 12px 20px rgba(44, 90, 157, 0.2);
}

.cnki-auth-form {
  display: grid;
  gap: 12px;
}

.cnki-auth-field {
  display: grid;
  gap: 7px;
}

.cnki-auth-field span {
  font-size: 13px;
  font-weight: 700;
  color: #45648d;
}

.cnki-auth-input {
  height: 44px;
  border-radius: 11px;
  border: 1px solid rgba(99, 130, 172, 0.45);
  background: #fff;
  padding: 0 12px;
  font-size: 14px;
  color: #234469;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.cnki-auth-input:focus {
  outline: none;
  border-color: rgba(45, 98, 175, 0.72);
  box-shadow: 0 0 0 3px rgba(46, 102, 178, 0.14);
}

.cnki-auth-code-row {
  display: flex;
  gap: 8px;
}

.cnki-auth-code-btn,
.cnki-auth-secondary,
.cnki-auth-submit,
.cnki-auth-ghost {
  border-radius: 11px;
  border: 0;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.cnki-auth-code-btn {
  min-width: 114px;
  height: 44px;
  border: 1px solid rgba(109, 137, 174, 0.42);
  background: rgba(240, 246, 255, 0.96);
  color: #44648f;
}

.cnki-auth-policy {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #60799a;
}

.cnki-auth-policy input {
  width: 14px;
  height: 14px;
}

.cnki-auth-submit {
  width: 100%;
  min-height: 44px;
  color: #fff;
  background: linear-gradient(135deg, #2460b7, #2f7fc8);
  box-shadow: 0 14px 22px rgba(42, 85, 152, 0.18);
}

.cnki-auth-submit:disabled,
.cnki-auth-code-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  box-shadow: none;
}

.cnki-auth-wx-shell {
  display: grid;
  gap: 11px;
}

.cnki-auth-wx-qr {
  border-radius: 14px;
  border: 1px dashed rgba(89, 124, 170, 0.46);
  background: #fff;
  min-height: 236px;
  display: grid;
  place-items: center;
  padding: 14px;
}

.cnki-auth-wx-qr-image {
  width: min(220px, 100%);
  height: auto;
}

.cnki-auth-wx-empty {
  font-size: 13px;
  color: #718aab;
}

.cnki-auth-wx-meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #5f789a;
}

.cnki-auth-wx-actions {
  display: flex;
  gap: 8px;
}

.cnki-auth-secondary {
  flex: 1;
  min-height: 42px;
  border: 1px solid rgba(109, 137, 174, 0.42);
  background: rgba(240, 246, 255, 0.96);
  color: #44648f;
}

.cnki-auth-wx-actions .cnki-auth-submit {
  flex: 1;
}

.cnki-auth-notice {
  margin: 0;
  border-radius: 11px;
  padding: 9px 11px;
  font-size: 13px;
  line-height: 1.6;
}

.cnki-auth-notice--error {
  border: 1px solid rgba(184, 75, 69, 0.25);
  background: rgba(255, 244, 242, 0.95);
  color: #ad4540;
}

.cnki-auth-notice--success {
  border: 1px solid rgba(25, 123, 82, 0.23);
  background: rgba(238, 250, 245, 0.95);
  color: #1f7756;
}

.cnki-auth-footer {
  margin-top: 2px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.cnki-auth-switch-link {
  font-size: 14px;
  font-weight: 700;
  color: #2758a3;
  text-decoration: none;
}

.cnki-auth-switch-link:hover {
  text-decoration: underline;
}

.cnki-auth-ghost {
  height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(114, 140, 174, 0.38);
  background: rgba(247, 251, 255, 0.95);
  color: #627d9d;
  font-size: 12px;
  font-weight: 600;
}

.cnki-auth-security-tip {
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
  color: #6c84a3;
}

@media (max-width: 980px) {
  .cnki-auth-shell {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .cnki-auth-right {
    border-left: 0;
    border-top: 1px solid rgba(72, 116, 177, 0.2);
  }

  .cnki-auth-brand-title {
    font-size: clamp(31px, 9vw, 44px);
  }
}

@media (max-width: 720px) {
  .cnki-auth-page {
    padding: 12px;
  }

  .cnki-auth-left,
  .cnki-auth-right {
    padding: 18px;
  }

  .cnki-auth-card {
    padding: 16px;
  }

  .cnki-auth-card-head h2 {
    font-size: 26px;
  }

  .cnki-auth-mode-switch,
  .cnki-auth-wx-actions {
    flex-direction: column;
  }

  .cnki-auth-mode-btn,
  .cnki-auth-code-btn,
  .cnki-auth-secondary,
  .cnki-auth-submit {
    width: 100%;
  }

  .cnki-auth-code-row {
    flex-direction: column;
  }
}
</style>
