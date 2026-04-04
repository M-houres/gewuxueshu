<template>
  <div class="login">
    <div class="login_top_con">
      <div class="login_header_box">
        <div class="login_header">
          <div class="login_header_left">
            <span class="login_brand_logo">格</span>
            <div class="login_brand_text">
              <strong>格物学术</strong>
            </div>
          </div>
          <div class="login_header_r">
            <span class="text">文稿检测</span>
            <span class="line"></span>
            <span class="text">AIGC检测</span>
            <span class="line"></span>
            <span class="text">文本优化</span>
            <span class="line"></span>
            <span class="text">答辩服务</span>
          </div>
        </div>
      </div>

      <main class="auth-board">
        <div class="auth-board__inner">
          <section class="auth-board__intro">
            <h1 class="auth-board__title">格物学术</h1>
            <p class="auth-board__lead">
              面向学术场景的综合服务平台，支持 AIGC 检测、降 AIGC 率、降重复率与答辩服务，流程清晰、结果可追踪。
            </p>
            <div class="auth-board__points">
              <p>1. 平台化上传与任务管理，进度实时可查。</p>
              <p>2. 支持多平台策略配置，适配不同学术场景。</p>
              <p>3. 积分计费透明，检测与处理记录统一归档。</p>
            </div>
          </section>

          <section class="auth-board__form">
            <div class="auth-form">
              <div class="auth-form__inner">
                <div class="login_form_title">
                  <div v-if="showLoginTypeTabs" class="login_type_tab">
                    <div class="login_type_tab_box">
                      <div
                        v-if="phoneLoginEnabled"
                        class="login_type_tab_item"
                        :class="{ active: mode === 'phone' }"
                        @click="switchMode('phone')"
                      >
                        验证码登录
                      </div>
                      <div
                        v-if="wechatLoginEnabled"
                        class="login_type_tab_item"
                        :class="{ active: mode === 'wx' }"
                        @click="switchMode('wx')"
                      >
                        微信扫码
                      </div>
                    </div>
                  </div>
                  <p class="login_mode_hint">{{ loginModeHint }}</p>
                  <p class="login_mode_hint login_mode_hint--sub">{{ thirdPartyHint }}</p>
                </div>

                <form v-if="mode === 'phone'" class="login_form_body" @submit.prevent="submitPhoneAuth">
                  <div class="login_input_box">
                    <input v-model.trim="phone" type="tel" maxlength="11" placeholder="请输入11位手机号" />
                  </div>

                  <div class="loginCodeBox">
                    <div class="code_input">
                      <input v-model.trim="code" maxlength="8" placeholder="请输入验证码" />
                    </div>
                    <div class="msgBtn" :class="{ disabledBtn: sending || countdown > 0 }">
                      <span @click="sendCode">{{ countdown > 0 ? `${countdown}s` : "获取验证码" }}</span>
                    </div>
                  </div>

                  <label class="isReadBox">
                    <input v-model="agreedPolicy" type="checkbox" />
                    <span class="userAgreementInfo">我已阅读并同意服务协议与隐私政策</span>
                  </label>

                  <button class="login_sub" :disabled="loading">
                    {{ loading ? "处理中..." : primaryButtonText }}
                  </button>

                  <div v-if="hasWechatEntry" class="third-auth">
                    <div class="third-auth__label">第三方登录</div>
                    <button type="button" class="third-auth__wechat" @click="switchMode('wx')">
                      微信扫码登录
                    </button>
                  </div>
                </form>

                <div v-else class="login_form_wechat_box">
                  <div class="imgCodeBox">
                    <img v-if="wxQrcodeDataUrl" :src="wxQrcodeDataUrl" alt="微信二维码" class="imgCode_img" />
                    <span v-else>二维码生成中</span>
                  </div>
                  <div class="wx_status_line">{{ wxStatusText }}，剩余 {{ wxCountdown }} 秒</div>
                  <div class="wx_actions">
                    <button type="button" @click="loadWxQrcode">刷新二维码</button>
                    <button v-if="wxMockEnabled" type="button" @click="mockWxAuthorize">模拟授权</button>
                  </div>
                </div>

                <p v-if="errorText" class="msg msg--error">{{ errorText }}</p>
                <p v-if="hintText" class="msg msg--ok">{{ hintText }}</p>

                <div class="registPwdBox">
                  <RouterLink :to="alternateEntryLink">{{ alternateEntryText }}</RouterLink>
                  <span class="registPwdLine"></span>
                  <button type="button" class="guest-link" @click="enterGuest">游客先浏览</button>
                </div>
              </div>

              <div class="login_bot_wechat_box">
                <span><img :src="loginFooterGzhImg" alt="" />微信公众号通知</span>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import loginFooterGzhImg from "../../../assets/cnki/login_footer_gzh_img.png"
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
const primaryButtonText = computed(() => (isRegisterPage.value ? "注册并进入工作台" : "登录并进入工作台"))
const alternateEntryText = computed(() => (isRegisterPage.value ? "已有账号，去登录" : "新用户注册"))
const wxStatusText = computed(() => {
  if (wxStatus.value === "authorized") return "已授权，正在登录"
  if (wxStatus.value === "expired") return "二维码已过期"
  return "等待扫码授权"
})
const showLoginTypeTabs = computed(() => phoneLoginEnabled.value && wechatLoginEnabled.value)
const hasWechatEntry = computed(() => wechatLoginEnabled.value)
const loginModeHint = computed(() => {
  if (showLoginTypeTabs.value) return "支持手机号验证码与微信扫码登录"
  if (wechatLoginEnabled.value) return "当前为微信扫码登录"
  return "当前为手机号验证码登录"
})
const thirdPartyHint = computed(() =>
  wechatLoginEnabled.value ? "支持第三方微信登录，支付通道由后台统一配置" : "第三方微信能力可在后台配置后启用"
)

watch([phoneLoginEnabled, wechatLoginEnabled], ([phoneEnabled, wxEnabled]) => {
  if (mode.value === "wx" && !wxEnabled) {
    mode.value = "phone"
    return
  }
  if (mode.value === "phone" && !phoneEnabled && wxEnabled) {
    mode.value = "wx"
  }
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
  if (redirect) params.set("redirect", redirect)

  const queryRef = route.query.ref
  if (typeof queryRef === "string" && queryRef.trim()) {
    referrerCode.value = queryRef.trim().toUpperCase()
    localStorage.setItem("wuhong_referrer_code", referrerCode.value)
    params.set("ref", referrerCode.value)
  } else {
    const cachedRef = localStorage.getItem("wuhong_referrer_code")
    referrerCode.value = cachedRef ? cachedRef.toUpperCase() : ""
    if (referrerCode.value) params.set("ref", referrerCode.value)
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
    if (!phoneLoginEnabled.value && wechatLoginEnabled.value) mode.value = "wx"
    if (!wechatLoginEnabled.value && phoneLoginEnabled.value) mode.value = "phone"
  } catch {
    wechatLoginEnabled.value = false
    wxMockEnabled.value = false
    phoneLoginEnabled.value = true
  }
}

async function switchMode(nextMode) {
  if (nextMode === "wx" && !wechatLoginEnabled.value) {
    errorText.value = "当前环境未开启微信登录"
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
    hintText.value = "验证码已发送，请注意查收"
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
    if (wxStatus.value === "expired") stopWxTimers()
  } catch {
    // noop
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
.login {
  min-height: 100vh;
  background: var(--bg-page);
  font-family: var(--font-sans);
}

.login_top_con {
  min-width: 0;
}

.login_header_box {
  background: var(--header-gradient-deep);
  border-bottom: 1px solid var(--header-border-deep);
  box-shadow: var(--header-shadow-deep);
}

.login_header {
  width: min(1200px, 100%);
  margin: 0 auto;
  height: 56px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.login_header_left {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.login_brand_logo {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #165dff;
  font-size: 14px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.88);
}

.login_brand_text {
  display: grid;
  min-width: 0;
}

.login_brand_text strong {
  color: var(--header-ink-deep);
  font-size: 16px;
  line-height: 1.1;
}

.login_brand_text span {
  color: var(--text-sub);
  font-size: 10px;
  line-height: 1.1;
  letter-spacing: 0.06em;
  display: none;
}

.login_header_r {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  row-gap: 6px;
}

.login_header_r .text {
  color: rgba(239, 247, 255, 0.96);
  font-size: 13px;
  line-height: 1.3;
  font-weight: 600;
}

.login_header_r .line {
  width: 1px;
  height: 14px;
  margin: 0 10px;
  background: rgba(232, 243, 255, 0.52);
}

.auth-board {
  width: min(1200px, 100%);
  margin: 0 auto;
  min-height: calc(100vh - 56px);
  padding: 24px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-board__inner {
  display: flex;
  width: 100%;
  max-width: 940px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 14px 34px rgba(22, 93, 255, 0.14);
  border: 1px solid #d7e5ff;
  background: #ffffff;
}

.auth-board__intro {
  flex: 1;
  padding: 40px 34px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: linear-gradient(152deg, #f4f8ff 0%, #ecf3ff 52%, #e5efff 100%);
  border-right: 1px solid #d8e7ff;
}

.auth-board__title {
  margin: 0;
  font-size: 30px;
  line-height: 1.25;
  font-weight: 700;
  color: #1d4fae;
}

.auth-board__lead {
  margin: 16px 0 0;
  font-size: 14px;
  line-height: 1.85;
  color: #4b638f;
  max-width: 500px;
}

.auth-board__points {
  margin-top: 20px;
  display: grid;
  gap: 10px;
}

.auth-board__points p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.7;
  color: #445b84;
}

.auth-board__form {
  width: 360px;
  flex-shrink: 0;
  background: #ffffff;
}

.auth-form {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.auth-form__inner {
  padding: 26px 24px 22px;
}

.login_mode_hint {
  margin: 0 0 14px;
  font-size: 12px;
  line-height: 1.4;
  color: #5f77a8;
}

.login_mode_hint--sub {
  margin-top: -8px;
  margin-bottom: 16px;
  color: #7a8fb8;
}

.login_type_tab_box {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.login_type_tab_item {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 18px;
  font-size: 13px;
  line-height: 36px;
  color: #555;
  background: #ffffff;
  cursor: pointer;
  border: 1px solid #dcdfe6;
}

.login_type_tab_item.active {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-light);
  font-weight: 600;
}

.login_input_box input,
.code_input input {
  width: 100%;
  height: 44px;
  border: 1px solid #dcdfe6;
  border-radius: var(--radius-input);
  background: #ffffff;
  padding: 0 12px;
  font-size: 14px;
  color: var(--text-main);
  outline: none;
}

.login_input_box input::placeholder,
.code_input input::placeholder {
  color: var(--text-placeholder);
}

.login_input_box input:focus,
.code_input input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.13);
}

.loginCodeBox {
  margin-top: 12px;
  position: relative;
}

.msgBtn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--primary);
  font-size: 12px;
  font-weight: 600;
}

.msgBtn.disabledBtn {
  color: #bfc4d2;
}

.msgBtn span {
  cursor: pointer;
}

.isReadBox {
  margin-top: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--text-sub);
}

.login_sub {
  margin-top: 14px;
  width: 100%;
  height: 48px;
  border: 0;
  border-radius: var(--radius-btn);
  background: var(--btn-primary-bg);
  color: #ffffff;
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  box-shadow: var(--btn-primary-shadow);
  transition: transform 0.16s ease, background-color 0.16s ease;
}

.login_sub:hover:not(:disabled) {
  background: var(--btn-primary-bg-hover);
  transform: translateY(-1px);
}

.login_sub:disabled {
  opacity: 0.65;
  box-shadow: none;
}

.third-auth {
  margin-top: 12px;
  border: 1px solid #d7e5ff;
  border-radius: 10px;
  padding: 10px 12px;
  background: #f7faff;
  display: grid;
  gap: 8px;
}

.third-auth__label {
  font-size: 12px;
  color: #5f77a8;
  line-height: 1.2;
}

.third-auth__wechat {
  width: 100%;
  min-height: 36px;
  border: 1px solid #bdd4ff;
  border-radius: 8px;
  background: #ffffff;
  color: #1758db;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease;
}

.third-auth__wechat:hover {
  background: #ecf4ff;
  border-color: #8fb4ff;
  color: #0f4ac5;
}

.login_form_wechat_box {
  display: grid;
  gap: 10px;
}

.imgCodeBox {
  border: 1px dashed #bfd4ff;
  border-radius: 10px;
  min-height: 220px;
  display: grid;
  place-items: center;
  background: #f5f9ff;
}

.imgCode_img {
  width: 190px;
  height: 190px;
}

.wx_status_line {
  font-size: 12px;
  color: var(--text-sub);
}

.wx_actions {
  display: inline-flex;
  gap: 8px;
}

.wx_actions button {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #ffffff;
  color: var(--text-sub);
  min-height: 32px;
  padding: 0 12px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.msg {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.55;
}

.msg--error {
  color: #b34a44;
}

.msg--ok {
  color: #1f7c58;
}

.registPwdBox {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 13px;
  line-height: 1.4;
}

.registPwdBox a,
.guest-link {
  color: var(--primary);
}

.registPwdLine {
  width: 1px;
  height: 12px;
  background: #d6dbe7;
}

.guest-link {
  border: 0;
  background: transparent;
  cursor: pointer;
}

.login_bot_wechat_box {
  min-height: 38px;
  line-height: 38px;
  text-align: center;
  background: #f0f5ff;
  border-top: 1px solid #d7e5ff;
  font-size: 12px;
  color: #5d7298;
}

.login_bot_wechat_box img {
  width: 16px;
  margin-right: 4px;
  vertical-align: middle;
}

@media (max-width: 1080px) {
  .auth-board {
    min-height: auto;
    padding: 16px 12px;
  }

  .auth-board__inner {
    flex-direction: column;
    max-width: 500px;
  }

  .auth-board__intro {
    padding: 24px 20px;
    border-right: none;
    border-bottom: 1px solid #dde4f0;
  }

  .auth-board__title {
    font-size: 24px;
  }

  .auth-board__lead {
    max-width: none;
  }

  .auth-board__form {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .login_header {
    height: auto;
    min-height: 56px;
    padding: 8px 12px;
    flex-direction: column;
    align-items: flex-start;
  }

  .login_brand_logo {
    width: 26px;
    height: 26px;
    font-size: 13px;
  }

  .login_brand_text strong {
    font-size: 15px;
  }

  .login_header_r .line {
    display: none;
  }

  .login_header_r {
    gap: 8px 10px;
  }

  .auth-board__title {
    font-size: 21px;
    line-height: 1.3;
  }

  .auth-board__lead {
    font-size: 14px;
    line-height: 1.7;
  }

  .auth-board__points p {
    font-size: 13px;
  }

  .auth-form__inner {
    padding: 18px 14px 14px;
  }

  .third-auth {
    gap: 6px;
    padding: 9px 10px;
  }

  .registPwdBox {
    gap: 8px;
    font-size: 12px;
  }
}
</style>
