<template>
  <div class="scholar-page academic-shell-enter">
    <div class="scholar-shell scholar-shell--editorial">
      <aside class="scholar-sidebar">
        <div class="scholar-brand">
          <div class="scholar-brand__eyebrow">学术工作台</div>
          <div class="scholar-brand__title">格物学术</div>
          <p class="scholar-brand__lead">检测、降重、降AIGC率、积分购买与个人中心统一在同一套流程内完成，减少重复跳转。</p>
        </div>

        <section class="scholar-sidebar__section">
          <div class="scholar-sidebar__label">核心功能</div>
          <nav class="scholar-nav">
            <RouterLink
              v-for="item in workspaceMenus"
              :key="item.path"
              :to="item.path"
              class="scholar-nav__item"
              :class="{ 'is-active': isMenuActive(item.path) }"
            >
              <span class="scholar-nav__label">{{ item.label }}</span>
            </RouterLink>
          </nav>
        </section>

        <section class="scholar-sidebar__section">
          <div class="scholar-sidebar__label">账户中心</div>
          <nav class="scholar-nav">
            <RouterLink
              v-for="item in accountMenus"
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
          <div class="scholar-rail-card__eyeline">账户状态</div>
          <div class="scholar-rail-card__headline">{{ hasUserToken ? '账户已连接' : '先体验后提交' }}</div>
          <div class="scholar-rail-card__grid">
            <div class="scholar-rail-card__metric">
              <span>当前功能</span>
              <strong>{{ activeMenu?.label || '工作台' }}</strong>
            </div>
            <div class="scholar-rail-card__metric">
              <span>当前积分</span>
              <strong>{{ displayCredits }}</strong>
            </div>
          </div>
          <div class="scholar-inline-actions" style="margin-top: 14px">
            <button v-if="hasUserToken" class="scholar-button" type="button" @click="goBuy">购买积分</button>
            <button v-else class="scholar-button" type="button" @click="goLogin">登录</button>
            <button
              class="scholar-button scholar-button--secondary"
              type="button"
              @click="hasUserToken ? logout() : goRegister()"
            >
              {{ hasUserToken ? '退出登录' : '注册账号' }}
            </button>
          </div>
        </div>
      </aside>

      <div class="scholar-main">
        <header class="scholar-topbar">
          <div class="scholar-topbar__meta">
            <div>
              <div class="scholar-topbar__eyebrow">当前工作区</div>
              <div class="scholar-topbar__title">{{ title }}</div>
              <p class="scholar-topbar__lead">{{ subtitle || '任务记录、积分流水与账户资料都统一沉淀在个人中心，便于回看与复核。' }}</p>
            </div>

            <div class="scholar-topbar__status">
              <span class="scholar-badge scholar-badge--info">{{ activeMenu?.label || '工作台' }}</span>
              <span class="scholar-badge scholar-badge--warn">当前积分 {{ displayCredits }}</span>
            </div>
          </div>

          <div class="scholar-topbar__brief">
            <article class="scholar-topbar__brief-item">
              <span>处理节奏</span>
              <strong>先选平台，再提交正文</strong>
              <p>三个功能入口共用同一套账户与计费体系，减少重复确认。</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>记录归档</span>
              <strong>个人中心统一查看</strong>
              <p>任务记录、积分流水和账户信息都汇总在一个页面中。</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>提交与支付</span>
              <strong>{{ hasUserToken ? '可直接提交任务' : '提交时再完成登录' }}</strong>
              <p>浏览流程不受影响，真正提交任务或支付时再完成验证即可。</p>
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
const workspaceMenus = [
  { path: "/app/detect", label: "AIGC检测" },
  { path: "/app/dedup", label: "降重复率" },
  { path: "/app/rewrite", label: "降AIGC率" },
]
const accountMenus = [
  { path: "/app/buy", label: "购买积分" },
  { path: "/app/profile", label: "个人中心" },
  { path: "/app/referral", label: "推广福利" },
]
const menus = [...workspaceMenus, ...accountMenus]

const activeMenu = computed(() => menus[findMenuIndex(route.path)] || menus[0])
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

function goRegister() {
  const redirect = encodeURIComponent(route.fullPath || "/app/detect")
  router.push(`/register?redirect=${redirect}`)
}

function isMenuActive(path) {
  return route.path === path || route.path.startsWith(`${path}/`)
}

function findMenuIndex(currentPath) {
  const index = menus.findIndex((item) => isRouteMatch(currentPath, item.path))
  return index >= 0 ? index : 0
}

function isRouteMatch(currentPath, targetPath) {
  return currentPath === targetPath || currentPath.startsWith(`${targetPath}/`)
}

function syncTokenState() {
  hasUserToken.value = Boolean(getUserToken())
}
</script>
