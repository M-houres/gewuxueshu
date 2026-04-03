<template>
  <div class="scholar-page academic-shell-enter">
    <div class="scholar-shell">
      <aside class="scholar-sidebar">
        <div class="scholar-brand">
          <div class="scholar-brand__eyebrow">运营后台</div>
          <div class="scholar-brand__title">运营控制台</div>
          <p class="scholar-brand__lead">
            把用户、订单、任务、推广、算法包和配置审计收进同一个后台，减少部署时反复改环境变量。
          </p>
        </div>

        <section class="scholar-sidebar__section">
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
          <div class="scholar-rail-card__eyeline">系统状态</div>
          <div class="scholar-rail-card__headline">{{ systemModeText }}</div>
          <div class="scholar-rail-card__body">
            运行模式由后台接口实时回读，避免界面状态和系统真实状态脱节。
          </div>
          <div class="scholar-rail-card__grid">
            <div class="scholar-rail-card__metric">
              <span>当前模块</span>
              <strong>{{ activeMenu?.label || "后台" }}</strong>
            </div>
            <div class="scholar-rail-card__metric">
              <span>管理员角色</span>
              <strong>{{ adminInfo?.role || "admin" }}</strong>
            </div>
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
              <div class="scholar-topbar__eyebrow">当前模块</div>
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

          <div class="scholar-topbar__brief">
            <article class="scholar-topbar__brief-item">
              <span>当前位置</span>
              <strong>{{ activeMenu?.label || "后台" }}</strong>
              <p>详情页和列表页共用同一导航高亮，避免丢失位置感。</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>管理方式</span>
              <strong>配置优先，环境变量兜底</strong>
              <p>关键参数统一沉到后台维护，部署后仍可在线调整。</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>权限边界</span>
              <strong>{{ adminInfo?.role || "admin" }}</strong>
              <p>超管专属能力会被路由守卫和接口权限同时约束。</p>
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
const route = useRoute()
const adminInfo = ref(getAdminInfo())
const systemMode = ref("LLM_PLUS_ALGO")

const coreMenus = computed(() => [
  { path: "/admin/dashboard", label: "总览看板" },
  { path: "/admin/users", label: "用户管理" },
  { path: "/admin/tasks", label: "任务管理" },
  { path: "/admin/orders", label: "订单管理" },
  { path: "/admin/referrals", label: "推广管理" },
  { path: "/admin/logs", label: "系统日志" },
])

const advancedMenus = computed(() => {
  if (adminInfo.value?.role !== "super_admin") {
    return []
  }
  return [
    { path: "/admin/algo-packages", label: "算法包管理" },
    { path: "/admin/configs", label: "配置中心" },
  ]
})

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
