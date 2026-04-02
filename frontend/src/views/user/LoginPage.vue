<template>
  <div class="scholar-auth academic-shell-enter">
    <div class="scholar-auth__frame">
      <section class="scholar-auth__poster">
        <div class="scholar-auth__content">
          <div class="scholar-auth__eyebrow">WuhongAI Academic Writing</div>
          <h1 class="scholar-auth__title">让论文修改、检测与交付回到同一工作流。</h1>
          <p class="scholar-auth__lead">
            面向学术文本处理的统一入口，支持 AIGC 检测、降重复率、降 AIGC 率、积分购买和任务记录回溯。
          </p>

          <div class="scholar-auth__points">
            <div class="scholar-auth__point">短信登录、微信扫码登录、游客浏览三种路径并存，先看后用。</div>
            <div class="scholar-auth__point">任务按字符精确计费，失败自动退款，状态与结果支持全程追踪。</div>
            <div class="scholar-auth__point">部署后支付、短信、微信登录、大模型都可在后台配置，无需反复改环境变量。</div>
          </div>
        </div>
      </section>

      <section class="scholar-auth__panel">
        <div class="scholar-stack">
          <div>
            <h2>登录</h2>
            <p class="scholar-lead" style="margin-top: 10px">
              {{ wechatLoginEnabled ? "支持短信验证码与微信扫码登录。" : "当前使用短信验证码登录。" }}
            </p>
          </div>

          <div class="scholar-switch" v-if="phoneLoginEnabled || wechatLoginEnabled">
            <button
              v-if="phoneLoginEnabled"
              type="button"
              class="scholar-switch__button"
              :class="{ 'is-active': mode === 'phone' }"
              @click="switchMode('phone')"
            >
              手机验证码
            </button>
            <button
              v-if="wechatLoginEnabled"
              type="button"
              class="scholar-switch__button"
              :class="{ 'is-active': mode === 'wx' }"
              @click="switchMode('wx')"
            >
              微信扫码
            </button>
          </div>

          <form v-if="mode === 'phone'" class="scholar-stack" @submit.prevent="login">
            <label class="scholar-field">
              <span class="scholar-field__label">手机号</span>
              <input
                v-model.trim="phone"
                class="scholar-input"
                autocomplete="tel"
                placeholder="请输入 11 位手机号"
              />
            </label>

            <label class="scholar-field">
              <span class="scholar-field__label">验证码</span>
              <div class="scholar-inline-actions" style="align-items: stretch">
                <input
                  v-model.trim="code"
                  class="scholar-input"
                  style="flex: 1"
                  autocomplete="one-time-code"
                  placeholder="请输入验证码"
                />
                <button
                  type="button"
                  class="scholar-button scholar-button--secondary"
                  :disabled="sending || countdown > 0"
                  @click="sendCode"
                >
                  {{ countdown > 0 ? `${countdown}s` : "发送验证码" }}
                </button>
              </div>
            </label>

            <button class="scholar-button" :disabled="loading">
              {{ loading ? "登录中..." : "登录并进入工作台" }}
            </button>
          </form>

          <div v-else class="scholar-panel scholar-panel--soft">
            <div class="scholar-panel__body">
              <div class="scholar-stack">
                <div class="scholar-note">
                  使用微信扫码完成授权。若当前是开发联调环境，可通过“模拟扫码成功”走通整条登录链路。
                </div>

                <div class="scholar-inline-actions" style="align-items: center">
                  <img
                    v-if="wxQrcodeDataUrl"
                    :src="wxQrcodeDataUrl"
                    alt="wx login qrcode"
                    class="rounded-[20px] border border-[var(--line)] bg-white"
                    style="height: 168px; width: 168px"
                  />

                  <div class="scholar-stack" style="min-width: 180px">
                    <span class="scholar-badge scholar-badge--info">状态：{{ wxStatusText }}</span>
                    <span class="scholar-pill">二维码剩余 {{ wxCountdown }} 秒</span>
                    <button
                      type="button"
                      class="scholar-button scholar-button--secondary"
                      @click="loadWxQrcode"
                    >
                      刷新二维码
                    </button>
                    <button
                      v-if="wxMockEnabled"
                      type="button"
                      class="scholar-button"
                      @click="mockWxAuthorize"
                    >
                      模拟扫码成功
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <p v-if="errorText" class="scholar-note scholar-note--danger">{{ errorText }}</p>
          <p v-if="hintText" class="scholar-note scholar-note--success">{{ hintText }}</p>

          <div class="scholar-inline-actions">
            <RouterLink class="scholar-button scholar-button--ghost" :to="registerLink">
              新用户注册
            </RouterLink>
            <button
              type="button"
              class="scholar-button scholar-button--secondary"
              @click="enterGuest"
            >
              先以游客浏览
            </button>
          </div>
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
  const refCode = route.query.ref
  if (typeof refCode === "string" && refCode) {
    localStorage.setItem("wuhong_referrer_code", refCode.toUpperCase())
    registerLink.value = `/register?ref=${encodeURIComponent(refCode)}`
  }
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
  const redirect = typeof route.query.redirect === "string" ? route.query.redirect : ""
  if (redirect && redirect.startsWith("/")) {
    router.push(redirect)
  } else {
    router.push("/app/detect")
  }
}

function enterGuest() {
  router.push("/app/detect")
}
</script>
