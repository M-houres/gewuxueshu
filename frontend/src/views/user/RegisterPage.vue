<template>
  <div class="auth-page">
    <div class="auth-shell">
      <section class="auth-hero">
        <p class="hero-kicker">GEWU ACADEMIC PLATFORM</p>
        <h1 class="hero-title">格物致知</h1>
        <p class="hero-desc">
          创建账号后即可进入统一工作台，使用 AIGC 检测、降重复率、降 AIGC 率能力，任务和积分记录集中管理。
        </p>
        <div class="hero-tags">
          <span>账号即开即用</span>
          <span>流程统一</span>
          <span>结果集中</span>
        </div>
      </section>

      <section class="auth-main">
        <div class="auth-card">
          <header class="auth-card__head">
            <span class="auth-chip">账号创建</span>
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

          <div class="card-foot">
            <RouterLink class="link-btn" :to="loginLink">返回登录</RouterLink>
          </div>
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
  display: grid;
  place-items: center;
  padding: clamp(16px, 3vw, 32px);
  background:
    radial-gradient(900px 520px at 12% 0%, rgba(253, 244, 224, 0.55), transparent 70%),
    radial-gradient(860px 500px at 92% 100%, rgba(212, 228, 236, 0.55), transparent 70%),
    #f2f5f7;
  font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", "Source Han Sans SC", sans-serif;
}

.auth-shell {
  width: min(960px, 100%);
  border-radius: 22px;
  border: 1px solid #d7dee5;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 24px 60px rgba(25, 45, 62, 0.1);
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
}

.auth-hero {
  padding: clamp(26px, 4.2vw, 44px);
  background:
    linear-gradient(154deg, #173f63 0%, #22576c 52%, #2b6675 100%),
    radial-gradient(circle at 85% 14%, rgba(244, 227, 194, 0.32), transparent 40%);
  color: #f4f8fc;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 16px;
}

.hero-kicker {
  margin: 0;
  letter-spacing: 0.18em;
  font-size: 11px;
  opacity: 0.74;
}

.hero-title {
  margin: 0;
  font-size: clamp(30px, 4.6vw, 46px);
  line-height: 1.08;
  letter-spacing: 0.08em;
  color: #fff7e7;
  font-family: "Source Han Serif SC", "Songti SC", "STSong", serif;
}

.hero-desc {
  margin: 0;
  max-width: 32ch;
  line-height: 1.8;
  font-size: 14px;
  color: rgba(244, 249, 252, 0.92);
}

.hero-tags {
  margin-top: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-tags span {
  border: 1px solid rgba(236, 244, 250, 0.3);
  background: rgba(236, 244, 250, 0.12);
  color: #eff5fb;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
}

.auth-main {
  padding: clamp(20px, 3.2vw, 34px);
  background: linear-gradient(180deg, #fbfcfd 0%, #f4f7fa 100%);
}

.auth-card {
  border: 1px solid #d9e2ea;
  border-radius: 16px;
  padding: clamp(18px, 2.6vw, 26px);
  background: #ffffff;
}

.auth-card__head h2 {
  margin: 8px 0 6px;
  font-size: 28px;
  color: #1b2a36;
  font-family: "Source Han Serif SC", "Songti SC", "STSong", serif;
}

.auth-card__head p {
  margin: 0;
  font-size: 14px;
  color: #5f6f7d;
}

.auth-chip {
  display: inline-flex;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: #145f4d;
  background: #e8f4ef;
}

.invite-note {
  margin-top: 10px !important;
  border-radius: 10px;
  border: 1px solid #cce8dc;
  background: #f1fbf5;
  color: #1c684f !important;
  padding: 8px 10px;
}

.form-stack {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  font-size: 13px;
  color: #4d6173;
}

.input {
  height: 42px;
  border: 1px solid #cad5df;
  border-radius: 11px;
  padding: 0 13px;
  background: #ffffff;
  color: #213142;
  font-size: 14px;
}

.input:focus {
  outline: none;
  border-color: #2f6584;
  box-shadow: 0 0 0 3px rgba(47, 101, 132, 0.14);
}

.code-row {
  display: flex;
  gap: 9px;
}

.btn {
  height: 42px;
  border: none;
  border-radius: 11px;
  padding: 0 14px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(134deg, #1a4f75, #266982);
  color: #ffffff;
}

.btn-light {
  background: #eaf1f6;
  color: #304456;
}

.message {
  margin: 12px 0 0;
  border-radius: 11px;
  padding: 9px 11px;
  font-size: 13px;
}

.message-error {
  border: 1px solid #efd1cb;
  background: #fff6f4;
  color: #a54137;
}

.message-success {
  border: 1px solid #cce8dc;
  background: #f1fbf5;
  color: #1c684f;
}

.card-foot {
  margin-top: 14px;
}

.link-btn {
  color: #1f6288;
  text-decoration: none;
  font-size: 14px;
  border-bottom: 1px solid rgba(31, 98, 136, 0.4);
  padding-bottom: 2px;
}

@media (max-width: 920px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .auth-hero {
    min-height: 220px;
  }
}
</style>
