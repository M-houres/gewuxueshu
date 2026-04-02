<template>
  <div class="academic-shell academic-shell-enter min-h-screen text-[#101822] md:grid md:grid-cols-[252px_1fr]">
    <aside class="relative border-b border-[#d8dde3] bg-gradient-to-b from-[#f8f7f2]/95 to-[#edf1f5]/95 p-5 md:min-h-screen md:border-b-0 md:border-r">
      <div class="mb-8">
        <div class="text-[11px] uppercase tracking-[0.2em] text-[#6f7c89]">格物学术 Academic Suite</div>
        <div class="mt-3 text-2xl font-semibold leading-tight">格物学术工作台</div>
        <p class="mt-2 text-xs text-[#5c6875]">AIGC检测 · 降重复率 · 降AIGC率</p>
      </div>
      <nav class="space-y-2 text-sm">
        <RouterLink
          v-for="(item, idx) in menus"
          :key="item.path"
          :to="item.path"
          class="group flex items-center justify-between rounded-xl px-3 py-2.5 transition"
          :class="$route.path === item.path ? 'bg-[#0f7a5f] text-white shadow-[0_8px_20px_rgba(27,77,65,0.25)]' : 'text-[#2d3b49] hover:bg-[#e7edf3]'"
        >
          <span>{{ item.label }}</span>
          <span class="text-[10px] tracking-[0.16em] opacity-70">{{ menuCode(idx) }}</span>
        </RouterLink>
      </nav>
      <div v-if="hasUserToken" class="mt-6 rounded-2xl border border-[#d4dce4] bg-white/90 p-4">
        <div class="text-xs tracking-[0.1em] text-[#687582]">当前积分</div>
        <div class="mt-1 text-3xl font-semibold">{{ displayCredits }}</div>
        <button class="mt-3 w-full rounded-xl bg-[#e7f2ee] px-3 py-2 text-sm text-[#0d6b52]" @click="goBuy">
          购买积分
        </button>
      </div>
      <div v-else class="mt-6 rounded-2xl border border-[#d4dce4] bg-white/90 p-4 text-sm text-[#5f6b78]">
        <div class="font-medium text-[#314150]">游客模式</div>
        <div class="mt-1 leading-6">可浏览功能页面，提交任务、查看个人数据时再登录。</div>
        <button class="mt-3 w-full rounded-xl bg-[#e7edf5] px-3 py-2 text-sm text-[#314150]" @click="goLogin">
          登录 / 注册
        </button>
      </div>
      <button
        v-if="hasUserToken"
        class="mt-4 w-full rounded-xl bg-[#eef2f6] px-3 py-2 text-sm text-[#2c3a45]"
        @click="logout"
      >
        退出登录
      </button>
      <button
        v-else
        class="mt-4 w-full rounded-xl bg-[#eef2f6] px-3 py-2 text-sm text-[#2c3a45]"
        @click="goLogin"
      >
        前往登录
      </button>
    </aside>

    <div>
      <header class="sticky top-0 z-10 flex min-h-16 items-center justify-between border-b border-[#d7dde3] bg-[#f7f8f6]/88 px-6 py-3 backdrop-blur">
        <div>
          <div class="text-[11px] uppercase tracking-[0.18em] text-[#7a8793]">Academic Workspace</div>
          <div class="mt-1 text-lg font-semibold">{{ title }}</div>
        </div>
        <div class="rounded-full bg-[#eaf0f6] px-3 py-1 text-sm text-[#566370]">{{ subtitle || "持续优化中" }}</div>
      </header>
      <main class="p-4 md:p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import { clearUserSession, getUserToken } from "../lib/session"

const props = defineProps({
  title: {
    type: String,
    default: "工作台",
  },
  subtitle: {
    type: String,
    default: "",
  },
  credits: {
    type: Number,
    default: null,
  },
})

const emit = defineEmits(["buy"])

const router = useRouter()
const route = useRoute()
const hasUserToken = ref(false)
const menus = [
  { path: "/app/detect", label: "AIGC检测" },
  { path: "/app/dedup", label: "降重复率" },
  { path: "/app/rewrite", label: "降AIGC率" },
  { path: "/app/history", label: "任务记录" },
  { path: "/app/buy", label: "购买积分" },
  { path: "/app/profile", label: "个人中心" },
  { path: "/app/referral", label: "推广福利" },
]

const displayCredits = computed(() => {
  if (props.credits == null) {
    return "--"
  }
  return props.credits.toLocaleString()
})

onMounted(syncTokenState)
watch(
  () => route.fullPath,
  () => syncTokenState()
)

function logout() {
  clearUserSession()
  hasUserToken.value = false
  router.push("/login")
}

function goBuy() {
  emit("buy")
  router.push("/app/buy")
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/detect")
  router.push(`/login?redirect=${redirect}`)
}

function menuCode(index) {
  return `S${String(index + 1).padStart(2, "0")}`
}

function syncTokenState() {
  hasUserToken.value = Boolean(getUserToken())
}
</script>
