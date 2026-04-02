<template>
  <div class="scholar-page academic-shell-enter">
    <div class="scholar-shell">
      <aside class="scholar-sidebar">
        <div class="scholar-brand">
          <div class="scholar-brand__eyebrow">WuhongAI Operations</div>
          <div class="scholar-brand__title">运营控制台</div>
          <p class="scholar-brand__lead">
            统一处理计费、支付、登录、算法包、推广和任务审计，面向上线运营的后台工作流。
          </p>
        </div>

        <nav class="scholar-nav">
          <RouterLink
            v-for="(item, idx) in menus"
            :key="item.path"
            :to="item.path"
            class="scholar-nav__item"
            :class="{ 'is-active': $route.path === item.path }"
          >
            <span class="scholar-nav__label">{{ item.label }}</span>
            <span class="scholar-nav__meta">{{ menuCode(idx) }}</span>
          </RouterLink>
        </nav>

        <div class="scholar-rail-card">
          <div class="scholar-rail-card__label">系统模式</div>
          <div class="scholar-rail-card__body" style="margin-top: 8px">
            <span class="scholar-badge" :class="systemModeBadgeClass">{{ systemModeText }}</span>
          </div>
        </div>

        <div class="scholar-rail-card">
          <div class="scholar-rail-card__label">当前管理员</div>
          <div class="scholar-rail-card__body">
            {{ adminInfo ? `${adminInfo.username} / ${adminInfo.role}` : "未识别管理员信息" }}
          </div>
          <button
            class="scholar-button scholar-button--secondary"
            style="margin-top: 14px; width: 100%"
            type="button"
            @click="logout"
          >
            退出后台
          </button>
        </div>
      </aside>

      <div class="scholar-main">
        <header class="scholar-topbar">
          <div class="scholar-topbar__meta">
            <div>
              <div class="scholar-topbar__eyebrow">Operations Console</div>
              <div class="scholar-topbar__title">{{ title }}</div>
              <p class="scholar-topbar__lead">
                {{ subtitle || "后台配置尽量收拢到管理界面，部署时减少环境变量依赖。" }}
              </p>
            </div>

            <div class="scholar-topbar__status">
              <span class="scholar-badge scholar-badge--info">
                {{ adminInfo?.role || "admin" }}
              </span>
              <span class="scholar-badge" :class="systemModeBadgeClass">
                {{ systemModeText }}
              </span>
            </div>
          </div>
        </header>

        <main class="scholar-content">
          <slot />
        </main>
      </div>
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
    { path: "/admin/dashboard", label: "总览看板" },
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
    return "算法降级模式"
  }
  return "大模型 + 算法"
})

const systemModeBadgeClass = computed(() => {
  if (systemMode.value === "ALGO_ONLY") {
    return "scholar-badge--danger"
  }
  return "scholar-badge--success"
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
