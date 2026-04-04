<template>
  <div class="app-wrapper">
    <header class="header-wrap">
      <div class="header-left">
        <div class="brand-block">
          <span class="brand-mark">格</span>
          <div class="brand-copy">
            <strong>格物学术</strong>
          </div>
        </div>
      </div>

      <div class="header-title" :class="{ 'header-title--hidden': shouldHideHeaderTitle }">{{ activeMenu?.label || "工作台" }}</div>

      <div class="header-right">
        <div class="header-notice">
          <span class="header-notice__tag">公告</span>
          <span class="header-notice__text">{{ headerNoticeText }}</span>
        </div>
        <button type="button" class="header-topup" @click="hasUserToken ? goBuy() : goLogin()">充值</button>
        <button type="button" class="header-link" @click="hasUserToken ? goProfile() : goLogin()">
          {{ hasUserToken ? "个人中心" : "登录" }}
        </button>
        <button type="button" class="header-link header-link--muted" @click="hasUserToken ? logout() : goRegister()">
          {{ hasUserToken ? "退出" : "注册" }}
        </button>
      </div>
    </header>

    <div class="content-wrap">
      <aside class="sider-wrap">
        <div class="scrollbar-wrapper">
          <ul class="el-menu">
            <li v-for="item in coreMenus" :key="item.path" class="menu-wrapper">
              <RouterLink :to="item.path" class="menu-link">
                <div class="el-menu-item" :class="{ 'is-active': isMenuActive(item.path) }">
                  <i class="siderIcon">
                    <component :is="item.icon" :size="14" />
                  </i>
                  <span class="subMenu_title_box">{{ item.label }}</span>
                </div>
              </RouterLink>
            </li>

            <li class="nav-divider" aria-hidden="true"></li>

            <li v-for="item in labMenus" :key="item.path" class="menu-wrapper">
              <div class="el-menu-item is-disabled" aria-disabled="true">
                <i class="siderIcon">
                  <component :is="item.icon" :size="14" />
                </i>
                <span class="subMenu_title_box">{{ item.label }}</span>
                <span class="menu-beta-badge">开发中</span>
              </div>
            </li>

            <li class="nav-divider" aria-hidden="true"></li>

            <li v-for="item in accountMenus" :key="item.path" class="menu-wrapper">
              <RouterLink :to="item.path" class="menu-link">
                <div class="el-menu-item" :class="{ 'is-active': isMenuActive(item.path) }">
                  <i class="siderIcon">
                    <component :is="item.icon" :size="14" />
                  </i>
                  <span class="subMenu_title_box">{{ item.label }}</span>
                </div>
              </RouterLink>
            </li>
          </ul>
        </div>
        <div class="sider-credits-card">
          <button type="button" class="sider-credits-card__buy-block" @click="hasUserToken ? goBuy() : goLogin()">购买积分</button>
          <div class="sider-credits-card__balance">
            <p class="sider-credits-card__balance-label">实时积分余额</p>
            <p class="sider-credits-card__balance-value">
              <span class="sider-credits-card__balance-number">{{ remainingCreditsNumber }}</span>
              <span class="sider-credits-card__balance-unit">积分</span>
            </p>
          </div>
        </div>
      </aside>

      <div class="main-wrap">
        <div class="main-content">
          <div v-if="!shouldHideTopbar" class="navbarCon">
            <div class="app-breadcrumb">
              <span>{{ activeMenu?.label || "工作台" }}</span>
              <span class="no-redirect">{{ title || activeMenu?.label || "页面" }}</span>
            </div>
            <div class="navbarCon_right">
              <button type="button" @click="router.back()">返回</button>
            </div>
          </div>

          <div class="app-main">
            <div class="app-main-con">
              <slot />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Bot, FilePenLine, FileSearch2, Gift, ScanSearch, ShieldCheck, UserRound } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import { userHttp } from "../lib/http"
import { clearUserSession, getUserToken } from "../lib/session"

const props = defineProps({
  title: {
    type: String,
    default: "",
  },
  subtitle: {
    type: String,
    default: "",
  },
  credits: {
    type: Number,
    default: null,
  },
  hideTopbar: {
    type: Boolean,
    default: false,
  },
  hideHeaderTitle: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(["buy"])

const router = useRouter()
const route = useRoute()
const hasUserToken = ref(false)
const DEFAULT_HEADER_NOTICE_TEXT = "平台系统持续优化中，任务提交后请在个人中心查看处理进度。"
const headerNoticeText = ref(DEFAULT_HEADER_NOTICE_TEXT)

const coreMenus = [
  { path: "/app/rewrite", label: "降AIGC率", icon: FilePenLine },
  { path: "/app/dedup", label: "降重复率", icon: FileSearch2 },
  { path: "/app/detect", label: "AIGC检测", icon: ScanSearch },
]

const labMenus = [
  { path: "/app/review", label: "智能审稿", icon: Bot },
  { path: "/app/defense", label: "答辩服务", icon: ShieldCheck },
]

const accountMenus = [
  { path: "/app/referral", label: "推广福利", icon: Gift },
  { path: "/app/profile", label: "个人中心", icon: UserRound },
]

const menus = [...coreMenus, ...labMenus, ...accountMenus]

const activeMenu = computed(() => menus.find((item) => isRouteMatch(route.path, item.path)) || menus[0])
const shouldHideHeaderTitle = computed(() => {
  if (props.hideHeaderTitle) return true
  return isRouteMatch(route.path, "/app/profile") || isRouteMatch(route.path, "/app/referral")
})
const shouldHideTopbar = computed(() => {
  if (props.hideTopbar) return true
  return isRouteMatch(route.path, "/app/profile") || isRouteMatch(route.path, "/app/referral")
})
const remainingCreditsNumber = computed(() => {
  if (typeof props.credits !== "number") return "--"
  return props.credits.toLocaleString()
})

onMounted(() => {
  syncTokenState()
  loadHeaderNotice()
})
watch(
  () => route.fullPath,
  () => syncTokenState()
)

async function loadHeaderNotice() {
  try {
    const data = await userHttp.get("/auth/options")
    const text = String(data?.header_notice_text || "").trim()
    headerNoticeText.value = text || DEFAULT_HEADER_NOTICE_TEXT
  } catch {
    headerNoticeText.value = DEFAULT_HEADER_NOTICE_TEXT
  }
}

function syncTokenState() {
  hasUserToken.value = Boolean(getUserToken())
}

function logout() {
  clearUserSession()
  hasUserToken.value = false
  router.push("/login")
}

function goBuy() {
  emit("buy")
  router.push("/app/buy")
}

function goProfile() {
  router.push("/app/profile")
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

function isRouteMatch(currentPath, targetPath) {
  return currentPath === targetPath || currentPath.startsWith(`${targetPath}/`)
}
</script>

<style scoped>
.app-wrapper {
  --sider-width: 196px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-page);
  color: var(--text-main);
}

.header-wrap {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 58px;
  display: grid;
  grid-template-columns: var(--sider-width) minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 0 18px;
  background: var(--header-gradient-deep);
  border-bottom: 1px solid var(--header-border-deep);
  box-shadow: var(--header-shadow-deep);
}

.header-left {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 0;
}

.brand-block {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.brand-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.96);
  color: #5f37c4;
  border: 1px solid rgba(255, 255, 255, 0.88);
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.brand-copy strong {
  font-size: 16px;
  line-height: 1.2;
  color: var(--header-ink-deep);
  letter-spacing: 0.02em;
}

.brand-copy span {
  font-size: 11px;
  line-height: 1.2;
  color: #7e6aa8;
  letter-spacing: 0.03em;
  display: none;
}

.header-topup {
  height: 31px;
  padding: 0 13px;
  border-radius: 10px;
  border: 1px solid #dac7f7;
  background: #ffffff;
  color: #5c3fc0;
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.01em;
  box-shadow: 0 1px 0 rgba(92, 63, 176, 0.08);
  cursor: pointer;
  transition: background-color 0.16s ease, border-color 0.16s ease, transform 0.16s ease, box-shadow 0.16s ease;
}

.header-topup:hover {
  background: #f8f3ff;
  border-color: #cdb1ff;
  color: #4f35af;
  transform: translateY(-1px);
  box-shadow: 0 5px 10px rgba(84, 56, 152, 0.16);
}

.header-topup:active {
  transform: translateY(0);
}

.header-notice {
  min-width: 0;
  max-width: 340px;
  height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid #dbcaf8;
  background: rgba(255, 255, 255, 0.72);
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.header-notice__tag {
  flex-shrink: 0;
  height: 18px;
  padding: 0 7px;
  border-radius: 999px;
  background: #efe5ff;
  color: #5b39b3;
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
}

.header-notice__text {
  min-width: 0;
  color: #624f86;
  font-size: 12px;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-title {
  justify-self: center;
  min-width: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--header-ink-deep);
  letter-spacing: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-title--hidden {
  visibility: hidden;
}

.header-right {
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.header-link {
  height: 31px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid #dac7f7;
  background: #ffffff;
  color: #5c3fc0;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1;
  box-shadow: 0 1px 0 rgba(92, 63, 176, 0.08);
  cursor: pointer;
  transition: background-color 0.16s ease, color 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}

.header-link:hover {
  background: #f8f3ff;
  color: #4f35af;
  border-color: #cdb1ff;
  transform: translateY(-1px);
}

.header-link:active {
  transform: translateY(0);
}

.header-link--muted {
  background: #ffffff;
  color: #5c3fc0;
  border: 1px solid #dac7f7;
  box-shadow: 0 1px 0 rgba(92, 63, 176, 0.08);
}

.header-link--muted:hover {
  background: #f8f3ff;
  color: #4f35af;
  border-color: #cdb1ff;
}

.content-wrap {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: var(--sider-width) minmax(0, 1fr);
  background: linear-gradient(180deg, #e6ebf4 0%, #f1f4fa 100%);
}

.sider-wrap {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  background: linear-gradient(180deg, #e1e7f1 0%, #eaf0f8 100%);
  overflow: hidden;
  box-shadow: inset -1px 0 0 rgba(44, 64, 92, 0.12);
}

.scrollbar-wrapper {
  flex: 1;
  overflow: auto;
  padding: 10px 0;
}

.sider-credits-card {
  margin: 8px 10px 14px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid #c7d8ec;
  background: linear-gradient(160deg, #f7fbff 0%, #eef5ff 54%, #e7f0fc 100%);
  box-shadow: 0 10px 22px rgba(24, 50, 84, 0.14);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sider-credits-card__buy-block {
  width: 100%;
  height: 38px;
  border-radius: 10px;
  border: 1px solid #d0c2ff;
  background: linear-gradient(135deg, #f4eeff 0%, #ece4ff 100%);
  color: #5d44ce;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease, transform 0.16s ease;
}

.sider-credits-card__buy-block:hover {
  background: #ece3ff;
  border-color: #b9a1ff;
  color: #4f38bd;
  transform: translateY(-1px);
}

.sider-credits-card__balance {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 6px;
  min-height: 82px;
  border-radius: 10px;
  border: 1px solid #d3e0f1;
  background: rgba(255, 255, 255, 0.84);
  padding: 10px 12px;
}

.sider-credits-card__balance-label {
  margin: 0;
  font-size: 12px;
  color: #5a6f8a;
  line-height: 1.4;
}

.sider-credits-card__balance-value {
  margin: 0;
  display: inline-flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 4px;
  line-height: 1.2;
  min-width: 0;
}

.sider-credits-card__balance-number {
  font-size: clamp(16px, 1.15vw, 21px);
  font-weight: 700;
  letter-spacing: 0.01em;
  color: #1f426f;
  max-width: 100%;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.sider-credits-card__balance-unit {
  font-size: 12px;
  line-height: 1.2;
  color: #5a6f8a;
  font-weight: 600;
}

.el-menu {
  margin: 0;
  padding: 0;
  list-style: none;
}

.menu-wrapper {
  list-style: none;
}

.menu-link {
  display: block;
  text-decoration: none;
}

.nav-divider {
  margin: 6px 16px;
  border-top: 1px solid #c3cfdf;
  list-style: none;
}

.el-menu-item {
  list-style: none;
  display: flex;
  align-items: center;
  gap: 8px;
  width: calc(100% - 16px);
  margin: 0 8px;
  min-height: 42px;
  padding: 11px 20px;
  border-radius: 10px;
  border-left: 3px solid transparent;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.45;
  color: #2f445f;
  background: transparent;
  transition: background-color 0.16s ease, color 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.el-menu-item:hover {
  background: #cfdaea;
  color: #1f3f67;
}

.el-menu-item.is-active {
  background: linear-gradient(135deg, #f8fbff 0%, #e8f0fc 100%);
  color: #1d3d65;
  font-weight: 600;
  border-left-color: var(--primary);
  box-shadow: 0 8px 18px rgba(34, 63, 104, 0.16);
}

.el-menu-item.is-disabled {
  cursor: default;
  opacity: 0.86;
}

.el-menu-item.is-disabled:hover {
  background: transparent;
  color: var(--text-sub);
}

.siderIcon {
  display: inline-flex;
  align-items: center;
  color: currentColor;
  flex-shrink: 0;
}

.subMenu_title_box {
  min-width: 0;
  flex: 1;
  color: inherit;
}

.menu-beta-badge {
  flex-shrink: 0;
  background: #fff3e0;
  color: #f57c00;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  line-height: 1.4;
}

.main-wrap {
  min-width: 0;
  padding: 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.34) 0%, rgba(255, 255, 255, 0) 32%);
}

.main-content {
  min-width: 0;
  max-width: 1280px;
  margin: 0 auto;
  display: grid;
  gap: 12px;
}

.navbarCon {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}

.app-breadcrumb {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 13px;
  color: var(--text-sub);
}

.app-breadcrumb .no-redirect {
  min-width: 0;
  font-size: 15px;
  color: var(--text-main);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.navbarCon_right button {
  height: 32px;
  border: 1px solid var(--btn-ghost-border);
  border-radius: 10px;
  background: var(--btn-ghost-bg);
  color: var(--btn-ghost-ink);
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
  padding: 0 12px;
  transition: border-color 0.16s ease, background-color 0.16s ease, color 0.16s ease, transform 0.16s ease;
}

.navbarCon_right button:hover {
  background: var(--btn-ghost-hover-bg);
  border-color: #bcc8e6;
  color: #3e4b6e;
  transform: translateY(-1px);
}

.navbarCon_right button:active {
  transform: translateY(0);
}

.app-main,
.app-main-con {
  min-width: 0;
}

@media (max-width: 980px) {
  .header-wrap {
    grid-template-columns: minmax(0, 1fr);
    height: auto;
    min-height: 56px;
    padding: 8px 12px;
    gap: 8px;
  }

  .header-title {
    justify-self: start;
  }

  .header-left {
    width: auto;
    flex-wrap: nowrap;
    gap: 0;
  }

  .header-notice {
    width: 100%;
    max-width: none;
    height: auto;
    min-height: 30px;
    border-radius: 8px;
    padding: 6px 10px;
  }

  .header-notice__text {
    white-space: normal;
  }

  .header-right {
    justify-self: start;
    flex-wrap: wrap;
  }

  .content-wrap {
    grid-template-columns: 1fr;
  }

  .sider-wrap {
    display: block;
    border-right: 0;
    border-bottom: 1px solid var(--border);
    overflow: auto;
  }

  .scrollbar-wrapper {
    overflow-x: auto;
    padding: 8px 0;
    flex: none;
  }

  .el-menu {
    display: flex;
    min-width: max-content;
  }

  .nav-divider {
    display: none;
  }

  .el-menu-item {
    min-height: 38px;
    padding: 10px 14px;
    border-left: 0;
    border-bottom: 3px solid transparent;
  }

  .el-menu-item.is-active {
    border-left: 0;
    border-bottom-color: var(--primary);
  }

  .main-wrap {
    padding: 16px;
  }

  .sider-credits-card {
    display: none;
  }
}
</style>
