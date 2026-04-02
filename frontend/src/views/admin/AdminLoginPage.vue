<template>
  <div class="scholar-auth academic-shell-enter">
    <div class="scholar-auth__frame" style="grid-template-columns: minmax(0, 1fr) minmax(380px, 430px)">
      <section class="scholar-auth__poster">
        <div class="scholar-auth__content">
          <div class="scholar-auth__eyebrow">WuhongAI Operations Access</div>
          <h1 class="scholar-auth__title">进入运营控制台。</h1>
          <p class="scholar-auth__lead">
            管理登录配置、支付配置、计费策略、算法包、任务审计和推广规则。生产环境下所有关键设置应从后台统一维护。
          </p>

          <div class="scholar-auth__points">
            <div class="scholar-auth__point">支付、短信、微信登录、大模型参数都支持在后台配置，不需要反复改部署脚本。</div>
            <div class="scholar-auth__point">后台配置保存后可立即生效，并带有就绪状态提示，适合商业化运营使用。</div>
          </div>
        </div>
      </section>

      <section class="scholar-auth__panel">
        <div class="scholar-stack">
          <div>
            <h2>后台登录</h2>
            <p class="scholar-lead" style="margin-top: 10px">
              输入管理员账号和密码，进入运营控制台。
            </p>
          </div>

          <form class="scholar-stack" @submit.prevent="login">
            <label class="scholar-field">
              <span class="scholar-field__label">用户名</span>
              <input
                v-model.trim="username"
                class="scholar-input"
                autocomplete="username"
                placeholder="请输入管理员用户名"
              />
            </label>

            <label class="scholar-field">
              <span class="scholar-field__label">密码</span>
              <input
                v-model.trim="password"
                type="password"
                class="scholar-input"
                autocomplete="current-password"
                placeholder="请输入密码"
              />
            </label>

            <button class="scholar-button" :disabled="loading">
              {{ loading ? "登录中..." : "登录后台" }}
            </button>
          </form>

          <p v-if="errorText" class="scholar-note scholar-note--danger">{{ errorText }}</p>

          <RouterLink class="scholar-button scholar-button--ghost" to="/login">
            返回用户登录
          </RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import { adminHttp } from "../../lib/http"
import { setAdminInfo, setAdminToken } from "../../lib/session"

const router = useRouter()
const route = useRoute()

const username = ref("")
const password = ref("")
const loading = ref(false)
const errorText = ref("")

async function login() {
  errorText.value = ""
  loading.value = true
  try {
    const data = await adminHttp.post("/admin/auth/login", {
      username: username.value,
      password: password.value,
    })
    setAdminToken(data.token)
    setAdminInfo(data.admin || null)
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : ""
    if (redirect && redirect.startsWith("/admin/")) {
      router.push(redirect)
    } else {
      router.push("/admin/dashboard")
    }
  } catch (error) {
    errorText.value = error.message || "登录失败"
  } finally {
    loading.value = false
  }
}
</script>
