<template>
  <div class="auth-page">
    <div class="auth-wrap">
      <section class="brand-panel">
        <p class="brand-kicker">GEWU SCHOLAR PLATFORM</p>
        <h1 class="brand-title">格物致知</h1>
        <p class="brand-desc">
          创建账号后即可使用 AIGC 检测、降重复率、降 AIGC 率。任务记录和积分流水统一在个人中心管理。
        </p>
      </section>

      <section class="form-panel">
        <header class="panel-head">
          <span class="panel-tag">账号创建</span>
          <h2>注册</h2>
          <p>请输入手机号和验证码完成注册。</p>
          <p v-if="referrerCode" class="invite-note">邀请码：{{ referrerCode }}</p>
        </header>

        <form class="form-stack" @submit.prevent="register">
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
            {{ loading ? "注册中..." : "完成注册" }}
          </button>
        </form>

        <p v-if="errorText" class="message message-error">{{ errorText }}</p>
        <p v-if="hintText" class="message message-success">{{ hintText }}</p>

        <div class="panel-foot">
          <RouterLink class="link-btn" :to="loginLink">返回登录</RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import { getDeviceFingerprint } from "../../lib/device"
import { userHttp } from "../../lib/http"
import { resolveUserRedirect } from "../../lib/redirect"
import { setUserInfo, setUserToken } from "../../lib/session"

const route = useRoute()
const router = useRouter()

const phone = ref("")
const code = ref("")
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)
const errorText = ref("")
const hintText = ref("")
const referrerCode = ref("")
const loginLink = ref("/login")
let timer = null

onMounted(() => {
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
    const cached = localStorage.getItem("wuhong_referrer_code")
    referrerCode.value = cached ? cached.toUpperCase() : ""
  }
  loginLink.value = params.toString() ? `/login?${params.toString()}` : "/login"
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

function validatePhone() {
  return /^1\d{10}$/.test(phone.value)
}

async function sendCode() {
  errorText.value = ""
  hintText.value = ""
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

async function register() {
  errorText.value = ""
  hintText.value = ""
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
    const data = await userHttp.post("/auth/login", {
      phone: phone.value,
      code: code.value,
      referrer_code: referrerCode.value || undefined,
      device_fingerprint: getDeviceFingerprint(),
    })
    setUserToken(data.token)
    setUserInfo(data.user)
    localStorage.removeItem("wuhong_referrer_code")
    router.push(resolveUserRedirect(route.query.redirect, "/app/detect"))
  } catch (error) {
    errorText.value = error.message || "注册失败"
  } finally {
    loading.value = false
  }
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

.invite-note {
  margin-top: 10px !important;
  border-radius: 10px;
  border: 1px solid #cde8dc;
  background: #f2fbf6;
  color: #17674f !important;
  padding: 8px 10px;
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
