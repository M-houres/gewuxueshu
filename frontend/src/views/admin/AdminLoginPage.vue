<template>
  <div class="min-h-screen p-4 md:flex md:items-center md:justify-center">
    <div class="w-full max-w-md rounded-3xl border border-[#d9dee4] bg-white p-7">
      <div class="text-[11px] uppercase tracking-[0.18em] text-[#6d7a86]">Operations Console</div>
      <h1 class="mt-3 text-3xl font-semibold">后台登录</h1>
      <p class="mt-1 text-sm text-[#5b6771]">请输入管理员账号与密码，进入运营控制台</p>
      <form class="mt-6 space-y-4" @submit.prevent="login">
        <label class="block space-y-2">
          <span class="text-sm text-[#4a5761]">用户名</span>
          <input v-model.trim="username" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2.5 outline-none focus:border-[#0f7a5f]" placeholder="请输入用户名" />
        </label>
        <label class="block space-y-2">
          <span class="text-sm text-[#4a5761]">密码</span>
          <input v-model.trim="password" type="password" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2.5 outline-none focus:border-[#0f7a5f]" placeholder="请输入密码" />
        </label>
        <button class="w-full rounded-xl bg-[#0f7a5f] px-4 py-2.5 text-white disabled:opacity-60" :disabled="loading">
          {{ loading ? "登录中..." : "登录后台" }}
        </button>
      </form>
      <p v-if="errorText" class="mt-3 text-sm text-[#af3f33]">{{ errorText }}</p>
      <RouterLink class="mt-6 block text-sm text-[#5b6771]" to="/login">返回用户登录</RouterLink>
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
