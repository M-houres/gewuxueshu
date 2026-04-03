<template>
  <div class="scholar-page academic-shell-enter">
    <div class="scholar-shell scholar-shell--editorial">
      <aside class="scholar-sidebar">
        <div class="scholar-brand">
          <div class="scholar-brand__eyebrow">学术工作台</div>
          <div class="scholar-brand__title">格物学术</div>
          <p class="scholar-brand__lead">
            把检测、降重、降 AIGC 率、积分购买和账户归档收进同一条工作流，减少跳转和反复确认。
          </p>
        </div>

        <section class="scholar-sidebar__section">
          <div class="scholar-sidebar__label">处理工作台</div>
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
          <div class="scholar-sidebar__label">账户与结算</div>
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
          <div class="scholar-rail-card__headline">{{ hasUserToken ? "已连接个人账户" : "浏览中，随时可登录" }}</div>
          <div class="scholar-rail-card__body">
            {{ hasUserToken ? "任务记录、积分流水和个人资料会统一归档到个人中心。" : "可以先了解功能流程；提交任务、支付或查看个人数据时再登录即可。" }}
          </div>
          <div class="scholar-rail-card__grid">
            <div class="scholar-rail-card__metric">
              <span>当前功能</span>
              <strong>{{ activeMenu?.label || "工作台" }}</strong>
            </div>
            <div class="scholar-rail-card__metric">
              <span>当前积分</span>
              <strong>{{ displayCredits }}</strong>
            </div>
          </div>
          <div class="scholar-inline-actions" style="margin-top: 14px">
            <button
              v-if="hasUserToken"
              class="scholar-button"
              type="button"
              @click="goBuy"
            >
              购买积分
            </button>
            <button
              v-else
              class="scholar-button"
              type="button"
              @click="goLogin"
            >
              登录继续
            </button>
            <button
              class="scholar-button scholar-button--secondary"
              type="button"
              @click="hasUserToken ? logout() : goRegister()"
            >
              {{ hasUserToken ? "退出登录" : "注册账号" }}
            </button>
          </div>
        </div>

        <div class="scholar-rail-card">
          <div class="scholar-rail-card__label">使用建议</div>
          <div class="scholar-rail-card__body">
            先选目标平台，再上传正文；任务记录和积分流水都会自动收进个人中心，便于回看和复核。
          </div>
        </div>
      </aside>

      <div class="scholar-main">
        <header class="scholar-topbar">
          <div class="scholar-topbar__meta">
            <div>
              <div class="scholar-topbar__eyebrow">当前工作区</div>
              <div class="scholar-topbar__title">{{ title }}</div>
              <p class="scholar-topbar__lead">
                {{ subtitle || "统一管理论文处理任务、结果下载、积分消费与账户资料。" }}
              </p>
            </div>

            <div class="scholar-topbar__status">
              <span class="scholar-badge scholar-badge--info">
                {{ activeMenu?.label || "工作台" }}
              </span>
              <span class="scholar-badge scholar-badge--warn">
                当前积分 {{ displayCredits }}
              </span>
            </div>
          </div>

          <div class="scholar-topbar__brief">
            <article class="scholar-topbar__brief-item">
              <span>处理节奏</span>
              <strong>先选择平台，再提交正文</strong>
              <p>不同任务入口共享同一套账户和计费体系，减少重复确认。</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>记录归档</span>
              <strong>个人中心统一查看</strong>
              <p>任务记录、积分流水和账户信息都收进一个账户页面，不再分散跳转。</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>账户状态</span>
              <strong>{{ hasUserToken ? "登录后自动同步数据" : "需要时再登录即可" }}</strong>
              <p>{{ hasUserToken ? "提交任务、查看结果和购买积分会自动回到当前账户。" : "浏览功能流程不受影响，提交任务或支付时再完成登录。" }}</p>
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
  { path: "/app/detect", label: "AIGC 检测" },
  { path: "/app/dedup", label: "降重复率" },
  { path: "/app/rewrite", label: "降 AIGC 率" },
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
