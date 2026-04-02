<template>
  <div class="min-h-screen p-4 md:flex md:items-center md:justify-center">
    <div class="w-full max-w-5xl overflow-hidden rounded-3xl border border-[#d9dee4] bg-white md:grid md:grid-cols-[1.2fr_1fr]">
      <section class="relative hidden min-h-[560px] bg-[linear-gradient(150deg,#1f5f4f,#274c67)] p-10 text-white md:block">
        <div class="text-xs uppercase tracking-[0.18em] text-[#cadce4]">格物学术</div>
        <h1 class="mt-6 text-4xl font-semibold leading-tight">新用户注册</h1>
        <p class="mt-4 max-w-md text-sm text-[#dce8ee]">通过手机号验证码快速注册，注册成功后自动登录并进入格物学术工作台。</p>
        <div class="mt-12 space-y-4 rounded-2xl border border-white/20 bg-white/10 p-5 text-sm text-[#e7f2f7]">
          <div>1. 邀请链接自动携带邀请码</div>
          <div>2. 注册关系自动绑定与奖励异步发放</div>
          <div>3. 完成后可立即使用三大核心功能</div>
        </div>
      </section>
      <section class="p-6 md:p-10">
        <div class="mb-8">
          <h2 class="text-2xl font-semibold text-[#101418]">注册</h2>
          <p class="mt-1 text-sm text-[#5b6771]">请输入手机号与验证码创建账号</p>
          <p v-if="referrerCode" class="mt-2 text-sm text-[#106c4f]">邀请码：{{ referrerCode }}</p>
        </div>

        <form class="space-y-4" @submit.prevent="register">
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
                class="rounded-xl bg-[#e6f2ee] px-3 text-sm text-[#0d6b52] disabled:opacity-60"
                :disabled="sending || countdown > 0"
                @click="sendCode"
              >
                {{ countdown > 0 ? `${countdown}s` : "发送验证码" }}
              </button>
            </div>
          </label>

          <button class="w-full rounded-xl bg-[#0f7a5f] px-4 py-2.5 text-white disabled:opacity-60" :disabled="loading">
            {{ loading ? "注册中..." : "注册并进入工作台" }}
          </button>
        </form>

        <p v-if="errorText" class="mt-3 text-sm text-[#b14133]">{{ errorText }}</p>
        <p v-if="hintText" class="mt-3 text-sm text-[#106c4f]">{{ hintText }}</p>

        <div class="mt-8 text-sm text-[#5b6771]">
          已有账号？<RouterLink class="text-[#0f7a5f]" to="/login">去登录</RouterLink>
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
    hintText.value = data.debug_code ? `测试验证码 ${data.debug_code}` : "验证码已发送"
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
