<template>
  <div class="min-h-screen p-4 md:flex md:items-center md:justify-center">
    <div class="w-full max-w-5xl overflow-hidden rounded-3xl border border-[#d9dee4] bg-white md:grid md:grid-cols-[1.2fr_1fr]">
      <section class="relative hidden min-h-[560px] bg-[linear-gradient(150deg,#1f5f4f,#274c67)] p-10 text-white md:block">
        <div class="text-xs uppercase tracking-[0.18em] text-[#d0e0e7]">格物学术</div>
        <h1 class="mt-6 text-4xl font-semibold leading-tight">学术文本处理平台</h1>
        <p class="mt-4 max-w-md text-sm text-[#d6ebe5]">
          AIGC检测、降重复率、降AIGC率统一入口，按平台规则计算积分，处理失败自动退回
        </p>
        <div class="mt-12 space-y-4 text-sm text-[#def0eb]">
          <div>1. 手机号验证码登录，支持邀请注册</div>
          <div>2. 微信扫码快速登录（开发环境可模拟）</div>
          <div>3. 任务与积分流水实时可查</div>
        </div>
      </section>
      <section class="p-6 md:p-10">
        <div class="mb-6">
          <h2 class="text-2xl font-semibold text-[#101418]">登录</h2>
          <p class="mt-1 text-sm text-[#5b6771]">{{ wechatLoginEnabled ? "手机号验证码 / 微信扫码" : "手机号验证码登录" }}</p>
        </div>

        <div class="mb-4 flex gap-2 rounded-xl bg-[#eef3f8] p-1">
          <button
            v-if="phoneLoginEnabled"
            class="rounded-lg px-3 py-2 text-sm transition"
            :class="mode === 'phone' ? 'bg-[#0f7a5f] text-white' : 'text-[#344250]'"
            @click="switchMode('phone')"
          >
            手机号登录
          </button>
          <button
            v-if="wechatLoginEnabled"
            class="rounded-lg px-3 py-2 text-sm transition"
            :class="mode === 'wx' ? 'bg-[#0f7a5f] text-white' : 'text-[#344250]'"
            @click="switchMode('wx')"
          >
            微信扫码
          </button>
        </div>

        <form v-if="mode === 'phone'" class="space-y-4" @submit.prevent="login">
          <label class="block space-y-2">
            <span class="text-sm text-[#4a5761]">手机号</span>
            <input
              v-model.trim="phone"
              class="w-full rounded-lg border border-[#ccd5dd] px-3 py-2 outline-none focus:border-[#0f7a5f]"
              placeholder="请输入11位手机号"
            />
          </label>
          <label class="block space-y-2">
            <span class="text-sm text-[#4a5761]">验证码</span>
            <div class="flex gap-2">
              <input
                v-model.trim="code"
                class="min-w-0 flex-1 rounded-lg border border-[#ccd5dd] px-3 py-2 outline-none focus:border-[#0f7a5f]"
                placeholder="请输入验证码"
              />
              <button
                type="button"
                class="rounded-lg bg-[#e6f2ee] px-3 text-sm text-[#0d6b52] disabled:opacity-60"
                :disabled="sending || countdown > 0"
                @click="sendCode"
              >
                {{ countdown > 0 ? `${countdown}s` : "发送验证码" }}
              </button>
            </div>
          </label>

          <button class="w-full rounded-lg bg-[#0f7a5f] px-4 py-2 text-white disabled:opacity-60" :disabled="loading">
            {{ loading ? "登录中..." : "登录并进入工作台" }}
          </button>
        </form>

        <div v-else class="rounded-xl border border-[#d9e2ea] bg-[#f8fbff] p-4">
          <div class="text-sm text-[#4d5d69]">请使用微信扫码登录</div>
          <div class="mt-3 flex items-center gap-4">
            <img v-if="wxQrcodeDataUrl" :src="wxQrcodeDataUrl" alt="wx login qrcode" class="h-40 w-40 rounded border border-[#dbe4ec]" />
            <div class="space-y-2 text-sm">
              <div>倒计时：{{ wxCountdown }} 秒</div>
              <div>状态：{{ wxStatusText }}</div>
              <button class="rounded bg-[#edf2f6] px-3 py-1.5 text-xs text-[#344250]" @click="loadWxQrcode">刷新二维码</button>
              <button
                v-if="wxMockEnabled"
                class="rounded bg-[#0f7a5f] px-3 py-1.5 text-xs text-white"
                @click="mockWxAuthorize"
              >
                模拟扫码成功
              </button>
            </div>
          </div>
        </div>

        <p v-if="errorText" class="mt-3 text-sm text-[#b14133]">{{ errorText }}</p>
        <p v-if="hintText" class="mt-3 text-sm text-[#106c4f]">{{ hintText }}</p>

        <div class="mt-8 text-sm text-[#5b6771]">
          新用户？<RouterLink class="text-[#0f7a5f]" :to="registerLink">去注册</RouterLink>
        </div>
        <button class="mt-3 text-sm text-[#5b6771] underline underline-offset-4" @click="enterGuest">
          先以游客模式浏览
        </button>
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
  if (String(route.query.mode || "") === "wx") {
    if (wechatLoginEnabled.value) {
      await switchMode("wx")
    }
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
    hintText.value = data.debug_code ? `测试验证码 ${data.debug_code}` : "验证码已发送"
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
