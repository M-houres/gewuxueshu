<template>
  <div class="scholar-page academic-shell-enter">
    <div class="scholar-shell scholar-shell--admin">
      <aside class="scholar-sidebar">
        <div class="scholar-brand">
          <div class="scholar-brand__eyebrow">运营后台</div>
          <div class="scholar-brand__title">格物学术</div>
          <p class="scholar-brand__lead">统一管理用户、任务、订单、推广、配置与审计，支持多管理员协同运营。</p>
        </div>

        <section v-if="coreMenus.length" class="scholar-sidebar__section">
          <div class="scholar-sidebar__label">核心运营</div>
          <nav class="scholar-nav">
            <RouterLink
              v-for="item in coreMenus"
              :key="item.path"
              :to="item.path"
              class="scholar-nav__item"
              :class="{ 'is-active': isMenuActive(item.path) }"
            >
              <span class="scholar-nav__label">{{ item.label }}</span>
            </RouterLink>
          </nav>
        </section>

        <section v-if="advancedMenus.length" class="scholar-sidebar__section">
          <div class="scholar-sidebar__label">系统能力</div>
          <nav class="scholar-nav">
            <RouterLink
              v-for="item in advancedMenus"
              :key="item.path"
              :to="item.path"
              class="scholar-nav__item"
              :class="{ 'is-active': isMenuActive(item.path) }"
            >
              <span class="scholar-nav__label">{{ item.label }}</span>
            </RouterLink>
          </nav>
        </section>

        <div class="scholar-rail-card scholar-rail-card--accent">
          <div class="scholar-rail-card__eyeline">当前账号</div>
          <div class="scholar-rail-card__headline">{{ adminInfo?.username || '未登录' }}</div>
          <div class="scholar-rail-card__body">
            角色：{{ roleLabel }}
            <br />
            模式：{{ systemModeText }}
          </div>
          <div class="scholar-inline-actions" style="margin-top: 12px">
            <button class="scholar-button scholar-button--secondary scholar-button--block" type="button" @click="logout">退出后台</button>
          </div>
        </div>
      </aside>

      <div class="scholar-main">
        <header class="scholar-topbar">
          <div class="scholar-topbar__meta">
            <div>
              <div class="scholar-topbar__eyebrow">当前模块</div>
              <div class="scholar-topbar__title">{{ title }}</div>
              <p class="scholar-topbar__lead">{{ subtitle || '后台配置尽量收敛到页面维护，减少依赖环境变量的手工操作。' }}</p>
            </div>

            <div class="scholar-topbar__status">
              <span class="scholar-badge scholar-badge--info">{{ roleLabel }}</span>
              <span class="scholar-badge" :class="systemModeBadgeClass">{{ systemModeText }}</span>
            </div>
          </div>

          <div class="scholar-topbar__brief">
            <article class="scholar-topbar__brief-item">
              <span>操作路径</span>
              <strong>{{ activeMenu?.label || '后台模块' }}</strong>
              <p>先筛选再处理，常用动作尽量在当前页完成，减少跳转。</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>权限分层</span>
              <strong>超管统一分配</strong>
              <p>普通管理员只看可见模块，默认收敛高风险操作。</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>生效机制</span>
              <strong>保存即生效</strong>
              <p>关键参数在线可维护，并保留审计日志便于追溯。</p>
            </article>
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
import { RouterLink, useRoute, useRouter } from "vue-router"

import { adminHttp } from "../lib/http"
import { adminHasPermission, clearAdminSession, getAdminInfo } from "../lib/session"

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
const route = useRoute()
const adminInfo = ref(getAdminInfo())
const systemMode = ref("LLM_PLUS_ALGO")

const roleLabel = computed(() => {
  if (adminInfo.value?.role === "super_admin") {
    return "超级管理员"
  }
  return "普通管理员"
})

const coreMenuDefs = [
  { path: "/admin/dashboard", label: "总览看板", permission: "dashboard:view" },
  { path: "/admin/users", label: "用户管理", permission: "users:view" },
  { path: "/admin/tasks", label: "任务管理", permission: "tasks:view" },
  { path: "/admin/orders", label: "订单管理", permission: "orders:view" },
  { path: "/admin/referrals", label: "推广管理", permission: "referrals:view" },
  { path: "/admin/logs", label: "系统日志", permission: "logs:view" },
]

const advancedMenuDefs = [
  { path: "/admin/algo-packages", label: "算法包管理", permission: "algo:view" },
  { path: "/admin/configs", label: "配置中心", permission: "configs:view" },
  { path: "/admin/admin-users", label: "管理员管理", permission: "admins:view" },
]

const coreMenus = computed(() => coreMenuDefs.filter((item) => adminHasPermission(item.permission)))
const advancedMenus = computed(() => advancedMenuDefs.filter((item) => adminHasPermission(item.permission)))

const menus = computed(() => [...coreMenus.value, ...advancedMenus.value])
const activeMenu = computed(() => menus.value.find((item) => isRouteMatch(route.path, item.path)) || menus.value[0] || null)

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
  if (!adminHasPermission("dashboard:view")) {
    return
  }
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

function isMenuActive(path) {
  return isRouteMatch(route.path, path)
}

function isRouteMatch(currentPath, targetPath) {
  if (targetPath === "/admin/users") {
    return currentPath === targetPath || currentPath.startsWith("/admin/users/")
  }
  return currentPath === targetPath || currentPath.startsWith(`${targetPath}/`)
}
</script>
