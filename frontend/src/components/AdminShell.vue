<template>
  <div class="academic-shell academic-shell-enter min-h-screen text-[#11161a] md:grid md:grid-cols-[252px_1fr]">
    <aside class="border-b border-[#d9dee4] bg-gradient-to-b from-[#f5f7fa]/95 to-[#eef2f6]/90 p-5 md:min-h-screen md:border-b-0 md:border-r">
      <div class="mb-8">
        <div class="text-[11px] uppercase tracking-[0.2em] text-[#667481]">格物学术 Console</div>
        <div class="mt-3 text-2xl font-semibold">运营后台</div>
        <p class="mt-2 text-xs text-[#5f6d79]">数据看板 · 任务审计 · 配置策略</p>
      </div>
      <nav class="space-y-2 text-sm">
        <RouterLink
          v-for="(item, idx) in menus"
          :key="item.path"
          :to="item.path"
          class="group flex items-center justify-between rounded-xl px-3 py-2.5 transition"
          :class="$route.path === item.path ? 'bg-[#0f7a5f] text-white shadow-[0_8px_20px_rgba(27,77,65,0.25)]' : 'text-[#26323b] hover:bg-[#e9eef4]'"
        >
          <span>{{ item.label }}</span>
          <span class="text-[10px] tracking-[0.16em] opacity-70">{{ menuCode(idx) }}</span>
        </RouterLink>
      </nav>
      <div class="mt-4 rounded-xl border border-[#d7e0e8] bg-[#f6faf8] px-3 py-2 text-xs text-[#355364]">
        <div class="flex items-center gap-2">
          <span class="inline-block h-2.5 w-2.5 rounded-full" :class="statusDotClass"></span>
          <span>{{ systemModeText }}</span>
        </div>
      </div>
      <button class="mt-4 w-full rounded-xl bg-[#edf1f5] px-3 py-2 text-sm text-[#33424f]" @click="logout">
        退出后台
      </button>
    </aside>

    <div>
      <header class="sticky top-0 z-10 flex min-h-16 items-center justify-between border-b border-[#d9dee4] bg-[#f4f6f9]/92 px-6 py-3 backdrop-blur">
        <div>
          <div class="text-[11px] uppercase tracking-[0.18em] text-[#73818d]">Operations Console</div>
          <div class="mt-1 text-lg font-semibold">{{ title }}</div>
        </div>
        <div class="flex items-center gap-3 text-sm text-[#5b6771]">
          <span class="rounded-full bg-[#e8edf2] px-3 py-1">{{ subtitle || "系统运行中" }}</span>
          <span v-if="adminInfo" class="rounded-full bg-[#dce6f2] px-3 py-1">{{ adminInfo.username }} · {{ adminInfo.role }}</span>
        </div>
      </header>
      <main class="p-4 md:p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import { RouterLink, useRouter } from "vue-router"

import { adminHttp } from "../lib/http"
import { clearAdminSession, getAdminInfo } from "../lib/session"

defineProps({
  title: {
    type: String,
    default: "后台",
  },
  subtitle: {
    type: String,
    default: "",
  },
})

const router = useRouter()
const adminInfo = ref(getAdminInfo())
const systemMode = ref("LLM_PLUS_ALGO")

const menus = computed(() => {
  const base = [
    { path: "/admin/dashboard", label: "仪表盘" },
    { path: "/admin/users", label: "用户管理" },
    { path: "/admin/tasks", label: "任务管理" },
    { path: "/admin/orders", label: "订单管理" },
    { path: "/admin/referrals", label: "推广管理" },
    { path: "/admin/logs", label: "系统日志" },
  ]
  if (adminInfo.value?.role === "super_admin") {
    base.splice(4, 0, { path: "/admin/algo-packages", label: "算法包管理" })
    base.push({ path: "/admin/configs", label: "配置中心" })
  }
  return base
})

const systemModeText = computed(() => {
  if (systemMode.value === "ALGO_ONLY") {
    return "仅算法模式（降级中）"
  }
  return "大模型 + 算法（正常）"
})

const statusDotClass = computed(() => {
  if (systemMode.value === "ALGO_ONLY") {
    return "bg-[#cf3d33]"
  }
  return "bg-[#13815d]"
})

onMounted(loadSystemStatus)

async function loadSystemStatus() {
  try {
    const data = await adminHttp.get("/admin/switch/current")
    systemMode.value = data.current_mode || "LLM_PLUS_ALGO"
  } catch {
    systemMode.value = "LLM_PLUS_ALGO"
  }
}

function logout() {
  clearAdminSession()
  router.push("/admin/login")
}

function menuCode(index) {
  return `A${String(index + 1).padStart(2, "0")}`
}
</script>
