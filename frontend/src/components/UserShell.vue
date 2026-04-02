<template>
  <div class="scholar-page academic-shell-enter">
    <div class="scholar-shell scholar-shell--editorial">
      <aside class="scholar-sidebar">
        <div class="scholar-brand">
          <div class="scholar-brand__eyebrow">GEWU ACADEMIC</div>
          <div class="scholar-brand__title">格物学术</div>
          <div class="scholar-brand__caption">Research Desk / {{ activeMenuCode }}</div>
          <p class="scholar-brand__lead">
            面向论文修改与检测场景的统一入口，覆盖 AIGC 检测、降重复率、降 AIGC 率、积分结算与结果回溯。
          </p>
        </div>

        <div class="scholar-rail-stack">
          <div class="scholar-rail-card scholar-rail-card--accent">
            <div class="scholar-rail-card__eyeline">当前工作区</div>
            <div class="scholar-rail-card__headline">{{ activeMenu?.label || "工作台" }}</div>
            <div class="scholar-rail-card__body">
              {{ hasUserToken ? "已进入正式会话，可直接提交任务、查看历史和管理积分。" : "当前仍可先浏览页面，创建任务或支付时再登录。" }}
            </div>
            <div class="scholar-rail-card__grid">
              <div class="scholar-rail-card__metric">
                <span>会话状态</span>
                <strong>{{ hasUserToken ? "用户模式" : "游客模式" }}</strong>
              </div>
              <div class="scholar-rail-card__metric">
                <span>工作区编号</span>
                <strong>{{ activeMenuCode }}</strong>
              </div>
            </div>
          </div>
        </div>

        <nav class="scholar-nav">
          <RouterLink
            v-for="(item, idx) in menus"
            :key="item.path"
            :to="item.path"
            class="scholar-nav__item"
            :class="{ 'is-active': isMenuActive(item.path) }"
          >
            <span class="scholar-nav__label">{{ item.label }}</span>
            <span class="scholar-nav__meta">{{ menuCode(idx) }}</span>
          </RouterLink>
        </nav>

        <div class="scholar-rail-card">
          <div class="scholar-rail-card__label">积分账户</div>
          <div class="scholar-rail-card__value">{{ displayCredits }}</div>
          <div class="scholar-rail-card__body">
            {{ hasUserToken ? "任务成功后按字符扣费，失败自动退回积分。" : "游客可先浏览页面，创建任务或支付时再登录。" }}
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
              登录使用
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
            建议先按目标平台选择算法，再提交正文；若有查重报告或 AIGC 报告，可一并上传以提升命中效率。
          </div>
        </div>
      </aside>

      <div class="scholar-main">
        <header class="scholar-topbar">
          <div class="scholar-topbar__meta">
            <div>
              <div class="scholar-topbar__eyebrow">GEWU ACADEMIC / {{ activeMenuCode }}</div>
              <div class="scholar-topbar__title">{{ title }}</div>
              <p class="scholar-topbar__lead">
                {{ subtitle || "统一管理论文处理任务、结果下载、积分消费与账户资料。" }}
              </p>
            </div>

            <div class="scholar-topbar__status">
              <span class="scholar-badge scholar-badge--info">
                {{ hasUserToken ? "已登录" : "游客模式" }}
              </span>
              <span class="scholar-badge scholar-badge--warn">
                当前积分 {{ displayCredits }}
              </span>
            </div>
          </div>

          <div class="scholar-topbar__brief">
            <article class="scholar-topbar__brief-item">
              <span>当前区段</span>
              <strong>{{ activeMenu?.label || "工作台" }}</strong>
              <p>任务、历史、支付和账户入口在同一工作区内切换。</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>访问方式</span>
              <strong>{{ hasUserToken ? "已登录会话" : "游客预览" }}</strong>
              <p>{{ hasUserToken ? "可直接创建任务并查看积分变化。" : "可先浏览页面，再决定登录或注册。" }}</p>
            </article>
            <article class="scholar-topbar__brief-item">
              <span>当前积分</span>
              <strong>{{ displayCredits }}</strong>
              <p>任务成功后按字符扣费，失败会自动退回积分。</p>
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
const menus = [
  { path: "/app/detect", label: "AIGC 检测" },
  { path: "/app/dedup", label: "降重复率" },
  { path: "/app/rewrite", label: "降 AIGC 率" },
  { path: "/app/history", label: "任务记录" },
  { path: "/app/buy", label: "购买积分" },
  { path: "/app/credits", label: "积分流水" },
  { path: "/app/profile", label: "个人中心" },
  { path: "/app/referral", label: "推广福利" },
]

const activeMenu = computed(() => menus[findMenuIndex(route.path)] || menus[0])
const activeMenuCode = computed(() => menuCode(findMenuIndex(route.path)))

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

function menuCode(index) {
  if (index < 0) {
    return "S00"
  }
  return `S${String(index + 1).padStart(2, "0")}`
}

function isMenuActive(path) {
  if (path === "/app/credits") {
    return route.path === path
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}

function findMenuIndex(currentPath) {
  const index = menus.findIndex((item) => isRouteMatch(currentPath, item.path))
  return index >= 0 ? index : 0
}

function isRouteMatch(currentPath, targetPath) {
  if (targetPath === "/app/credits") {
    return currentPath === targetPath
  }
  return currentPath === targetPath || currentPath.startsWith(`${targetPath}/`)
}

function syncTokenState() {
  hasUserToken.value = Boolean(getUserToken())
}
</script>
