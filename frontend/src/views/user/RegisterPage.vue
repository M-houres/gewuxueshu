<template>
  <div class="scholar-auth scholar-auth--register academic-shell-enter">
    <div class="scholar-auth__frame scholar-auth__frame--editorial">
      <section class="scholar-auth__poster">
        <div class="scholar-auth__content scholar-auth__content--login">
          <div class="scholar-auth__masthead">
            <div>
              <div class="scholar-auth__eyebrow">GEWU ACADEMIC</div>
              <div class="scholar-login__meta">Invite / Auto Onboarding</div>
            </div>
            <span class="scholar-auth__signal">Invite Tracking / Auto Login</span>
          </div>

          <div class="scholar-auth__headline">
            <h1 class="scholar-auth__title scholar-auth__title--login">格物学术</h1>
            <p class="scholar-auth__lead scholar-auth__lead--login">
              两步完成注册，成功后自动登录，直接进入检测、降重、降 AIGC 率和积分购买流程。
            </p>
          </div>

          <div class="scholar-auth__ledger">
            <div class="scholar-auth__ledger-label">注册后的账户结构</div>
            <div class="scholar-auth__ledger-grid">
              <article class="scholar-auth__ledger-card">
                <div class="scholar-auth__ledger-index">01</div>
                <strong>邀请关系</strong>
                <p>邀请链接可自动带入推荐码，奖励按后台规则结算。</p>
              </article>
              <article class="scholar-auth__ledger-card">
                <div class="scholar-auth__ledger-index">02</div>
                <strong>手机号开通</strong>
                <p>验证通过后立即创建账户，不再额外收集注册资料。</p>
              </article>
              <article class="scholar-auth__ledger-card">
                <div class="scholar-auth__ledger-index">03</div>
                <strong>统一归档</strong>
                <p>账号、积分流水和历史任务都回到个人中心统一维护。</p>
              </article>
            </div>
          </div>

          <div class="scholar-auth__timeline">
            <article class="scholar-auth__timeline-item">
              <span class="scholar-auth__timeline-dot"></span>
              <div>
                <div class="scholar-auth__timeline-code">STEP 01</div>
                <div class="scholar-auth__timeline-title">识别邀请码</div>
                <p class="scholar-auth__timeline-copy">
                  支持链接自动带入推荐码，也支持从本地缓存继续注册。
                </p>
              </div>
            </article>
            <article class="scholar-auth__timeline-item">
              <span class="scholar-auth__timeline-dot"></span>
              <div>
                <div class="scholar-auth__timeline-code">STEP 02</div>
                <div class="scholar-auth__timeline-title">短信验证创建账户</div>
                <p class="scholar-auth__timeline-copy">
                  无需额外填写昵称或资料，注册完成后直接可用。
                </p>
              </div>
            </article>
            <article class="scholar-auth__timeline-item">
              <span class="scholar-auth__timeline-dot"></span>
              <div>
                <div class="scholar-auth__timeline-code">STEP 03</div>
                <div class="scholar-auth__timeline-title">自动进入工作台</div>
                <p class="scholar-auth__timeline-copy">
                  立即开始检测、降重和积分购买，不中断任务流程。
                </p>
              </div>
            </article>
          </div>
        </div>
      </section>

      <section class="scholar-auth__panel">
        <div class="scholar-auth__form-shell scholar-stack">
          <div class="scholar-auth__panel-head">
            <span class="scholar-badge scholar-badge--info">账户创建</span>
            <h2>注册</h2>
            <p class="scholar-lead">
              输入手机号和验证码即可创建账号。
            </p>
            <p v-if="referrerCode" class="scholar-note scholar-note--success">
              当前邀请码：{{ referrerCode }}
            </p>
          </div>

          <div class="scholar-auth__quickline">
            <article class="scholar-auth__quickitem">
              <span>登录状态</span>
              <strong>注册后自动登录</strong>
            </article>
            <article class="scholar-auth__quickitem">
              <span>邀请关系</span>
              <strong>{{ referrerCode ? "已自动识别" : "可稍后补充" }}</strong>
            </article>
            <article class="scholar-auth__quickitem">
              <span>可用范围</span>
              <strong>立即进入工作台</strong>
            </article>
          </div>

          <form class="scholar-stack scholar-stack--compact" @submit.prevent="register">
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
              {{ loading ? "注册中..." : "注册并进入工作台" }}
            </button>
          </form>

          <p v-if="errorText" class="scholar-note scholar-note--danger">{{ errorText }}</p>
          <p v-if="hintText" class="scholar-note scholar-note--success">{{ hintText }}</p>

          <div class="scholar-inline-actions scholar-inline-actions--spread">
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
