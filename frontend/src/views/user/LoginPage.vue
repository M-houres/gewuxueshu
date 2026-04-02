<template>
  <div class="scholar-auth scholar-auth--login academic-shell-enter">
    <div class="scholar-auth__frame scholar-auth__frame--editorial">
      <section class="scholar-auth__poster scholar-auth__poster--login">
        <div class="scholar-auth__content scholar-auth__content--login">
          <div class="scholar-auth__masthead">
            <div>
              <div class="scholar-auth__eyebrow">GEWU ACADEMIC</div>
              <div class="scholar-login__meta">学术文本工作流平台</div>
            </div>
            <span class="scholar-auth__signal">Research Workflow / 24H</span>
          </div>

          <div class="scholar-auth__headline">
            <h1 class="scholar-auth__title scholar-auth__title--login">格物学术</h1>
            <p class="scholar-auth__lead scholar-auth__lead--login">
              论文检测、降重与文本优化，在一套更清晰、更稳定的工作流内完成。
            </p>
          </div>

          <div class="scholar-auth__ledger">
            <div class="scholar-auth__ledger-label">从检测到交付</div>
            <div class="scholar-auth__ledger-grid">
              <article class="scholar-auth__ledger-card">
                <div class="scholar-auth__ledger-index">01</div>
                <strong>AIGC 检测</strong>
                <p>先识别文本生成痕迹，再决定是否进入降重或改写流程。</p>
              </article>
              <article class="scholar-auth__ledger-card">
                <div class="scholar-auth__ledger-index">02</div>
                <strong>降重复率</strong>
                <p>按目标平台选择算法，保留学术表达的结构稳定性。</p>
              </article>
              <article class="scholar-auth__ledger-card">
                <div class="scholar-auth__ledger-index">03</div>
                <strong>结果交付</strong>
                <p>处理完成后回到同一工作台，统一下载结果与历史记录。</p>
              </article>
            </div>
          </div>

          <div class="scholar-auth__timeline">
            <article class="scholar-auth__timeline-item">
              <span class="scholar-auth__timeline-dot"></span>
              <div>
                <div class="scholar-auth__timeline-code">STEP 01</div>
                <div class="scholar-auth__timeline-title">提交正文或报告</div>
                <p class="scholar-auth__timeline-copy">
                  支持先查看页面结构，再决定是否登录创建任务。
                </p>
              </div>
            </article>
            <article class="scholar-auth__timeline-item">
              <span class="scholar-auth__timeline-dot"></span>
              <div>
                <div class="scholar-auth__timeline-code">STEP 02</div>
                <div class="scholar-auth__timeline-title">执行检测与优化</div>
                <p class="scholar-auth__timeline-copy">
                  按字符精确计费，失败自动退回积分，过程状态全程可见。
                </p>
              </div>
            </article>
            <article class="scholar-auth__timeline-item">
              <span class="scholar-auth__timeline-dot"></span>
              <div>
                <div class="scholar-auth__timeline-code">STEP 03</div>
                <div class="scholar-auth__timeline-title">回到同一工作台交付</div>
                <p class="scholar-auth__timeline-copy">
                  下载结果、查看积分流水和回溯历史任务都在一个入口内完成。
                </p>
              </div>
            </article>
          </div>

          <div class="scholar-login__footnote">
            适用于毕业论文、课程论文、期刊初稿等常见学术文本场景。
          </div>
        </div>
      </section>

      <section class="scholar-auth__panel">
        <div class="scholar-auth__form-shell scholar-stack">
          <div class="scholar-auth__panel-head">
            <span class="scholar-badge scholar-badge--info">统一登录入口</span>
            <h2>登录</h2>
            <p class="scholar-lead">
              {{ wechatLoginEnabled ? "支持短信验证码与微信扫码登录。" : "当前使用短信验证码登录。" }}
            </p>
          </div>

          <div class="scholar-auth__quickline">
            <article class="scholar-auth__quickitem">
              <span>访问方式</span>
              <strong>{{ wechatLoginEnabled ? "短信 / 微信" : "短信验证码" }}</strong>
            </article>
            <article class="scholar-auth__quickitem">
              <span>试用方式</span>
              <strong>游客可先浏览</strong>
            </article>
            <article class="scholar-auth__quickitem">
              <span>结果管理</span>
              <strong>任务全程可追踪</strong>
            </article>
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

          <form v-if="mode === 'phone'" class="scholar-stack scholar-stack--compact" @submit.prevent="login">
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

            <button class="scholar-button scholar-button--block" :disabled="loading">
              {{ loading ? "登录中..." : "登录并进入工作台" }}
            </button>
          </form>

          <div v-else class="scholar-auth__wx-shell">
            <div class="scholar-note">
              使用微信扫码完成授权。若当前是开发联调环境，可通过“模拟扫码成功”走通整条登录链路。
            </div>

            <div class="scholar-auth__wx-board">
              <div class="scholar-auth__qr">
                <img
                  v-if="wxQrcodeDataUrl"
                  :src="wxQrcodeDataUrl"
                  alt="wx login qrcode"
                  class="scholar-auth__qr-image"
                />
                <span v-else class="scholar-auth__qr-empty">等待生成二维码</span>
              </div>

              <div class="scholar-auth__wx-meta">
                <span class="scholar-badge scholar-badge--info">状态：{{ wxStatusText }}</span>
                <span class="scholar-pill">二维码剩余 {{ wxCountdown }} 秒</span>
                <p class="scholar-auth__microcopy">授权成功后会自动跳转到工作台。</p>
                <button
                  type="button"
                  class="scholar-button scholar-button--secondary scholar-button--block"
                  @click="loadWxQrcode"
                >
                  刷新二维码
                </button>
                <button
                  v-if="wxMockEnabled"
                  type="button"
                  class="scholar-button scholar-button--block"
                  @click="mockWxAuthorize"
                >
                  模拟扫码成功
                </button>
              </div>
            </div>
          </div>

          <p v-if="errorText" class="scholar-note scholar-note--danger">{{ errorText }}</p>
          <p v-if="hintText" class="scholar-note scholar-note--success">{{ hintText }}</p>

          <div class="scholar-inline-actions scholar-inline-actions--spread">
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

function enterGuest() {
  router.push("/app/detect")
}
</script>
