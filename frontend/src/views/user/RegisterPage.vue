<template>
  <div class="scholar-auth academic-shell-enter">
    <div class="scholar-auth__frame">
      <section class="scholar-auth__poster">
        <div class="scholar-auth__content">
          <div class="scholar-auth__eyebrow">WuhongAI New Account</div>
          <h1 class="scholar-auth__title">创建学术工作台账号。</h1>
          <p class="scholar-auth__lead">
            注册成功后自动登录，可直接进入检测、降重、降 AIGC 率和积分购买流程。
          </p>

          <div class="scholar-auth__points">
            <div class="scholar-auth__point">支持邀请链接自动带入推荐码，注册关系和奖励按后台规则自动生效。</div>
            <div class="scholar-auth__point">手机号验证通过后立即创建账户，无需再走额外资料流程。</div>
            <div class="scholar-auth__point">后续账号、昵称、积分流水和历史任务都在个人中心统一维护。</div>
          </div>
        </div>
      </section>

      <section class="scholar-auth__panel">
        <div class="scholar-stack">
          <div>
            <h2>注册</h2>
            <p class="scholar-lead" style="margin-top: 10px">
              输入手机号和验证码即可创建账号。
            </p>
            <p v-if="referrerCode" class="scholar-note scholar-note--success" style="margin-top: 14px">
              当前邀请码：{{ referrerCode }}
            </p>
          </div>

          <form class="scholar-stack" @submit.prevent="register">
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
              {{ loading ? "注册中..." : "注册并进入工作台" }}
            </button>
          </form>

          <p v-if="errorText" class="scholar-note scholar-note--danger">{{ errorText }}</p>
          <p v-if="hintText" class="scholar-note scholar-note--success">{{ hintText }}</p>

          <div class="scholar-inline-actions">
            <RouterLink class="scholar-button scholar-button--ghost" to="/login">
              返回登录
            </RouterLink>
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
let timer = null

onMounted(() => {
  const queryRef = route.query.ref
  if (typeof queryRef === "string" && queryRef.trim()) {
    referrerCode.value = queryRef.trim().toUpperCase()
    localStorage.setItem("wuhong_referrer_code", referrerCode.value)
    return
  }
  const cached = localStorage.getItem("wuhong_referrer_code")
  referrerCode.value = cached ? cached.toUpperCase() : ""
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
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
    if (timer) {
      clearInterval(timer)
    }
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) {
        clearInterval(timer)
      }
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
    router.push("/app/detect")
  } catch (error) {
    errorText.value = error.message || "注册失败"
  } finally {
    loading.value = false
  }
}
</script>
