<template>
  <div class="scholar-auth scholar-auth--admin academic-shell-enter">
    <div class="scholar-auth__frame scholar-auth__frame--editorial scholar-auth__frame--admin">
      <section class="scholar-auth__poster">
        <div class="scholar-auth__content scholar-auth__content--login">
          <div class="scholar-auth__masthead">
            <div>
              <div class="scholar-auth__eyebrow">OPERATIONS CONSOLE</div>
              <div class="scholar-login__meta">Deploy / Billing / Audit</div>
            </div>
            <span class="scholar-auth__signal">Prod-ready Controls</span>
          </div>

          <div class="scholar-auth__headline">
            <h1 class="scholar-auth__title scholar-auth__title--login">格物学术运营后台</h1>
            <p class="scholar-auth__lead scholar-auth__lead--login">
              管理登录配置、支付配置、计费策略、算法包、任务审计和推广规则。生产环境下的关键设置应从后台统一维护。
            </p>
          </div>

          <div class="scholar-auth__ledger">
            <div class="scholar-auth__ledger-label">后台控制面</div>
            <div class="scholar-auth__ledger-grid">
              <article class="scholar-auth__ledger-card">
                <div class="scholar-auth__ledger-index">A1</div>
                <strong>登录与安全</strong>
                <p>统一管理短信、微信登录、管理员账号和上线环境密钥。</p>
              </article>
              <article class="scholar-auth__ledger-card">
                <div class="scholar-auth__ledger-index">A2</div>
                <strong>支付与计费</strong>
                <p>后台配置计费策略、支付回调与积分套餐，减少部署脚本改动。</p>
              </article>
              <article class="scholar-auth__ledger-card">
                <div class="scholar-auth__ledger-index">A3</div>
                <strong>审计与回溯</strong>
                <p>任务、订单、推广和算法包都回到同一控制台中统一审计。</p>
              </article>
            </div>
          </div>

          <div class="scholar-auth__timeline">
            <article class="scholar-auth__timeline-item">
              <span class="scholar-auth__timeline-dot"></span>
              <div>
                <div class="scholar-auth__timeline-code">CONTROL 01</div>
                <div class="scholar-auth__timeline-title">后台保存立即生效</div>
                <p class="scholar-auth__timeline-copy">
                  支付、短信、微信登录和模型参数尽量收拢到管理界面统一维护。
                </p>
              </div>
            </article>
            <article class="scholar-auth__timeline-item">
              <span class="scholar-auth__timeline-dot"></span>
              <div>
                <div class="scholar-auth__timeline-code">CONTROL 02</div>
                <div class="scholar-auth__timeline-title">就绪状态回读</div>
                <p class="scholar-auth__timeline-copy">
                  配置是否完整、是否可用都通过控制台状态回读，而不是只依赖部署猜测。
                </p>
              </div>
            </article>
            <article class="scholar-auth__timeline-item">
              <span class="scholar-auth__timeline-dot"></span>
              <div>
                <div class="scholar-auth__timeline-code">CONTROL 03</div>
                <div class="scholar-auth__timeline-title">日志与任务统一审计</div>
                <p class="scholar-auth__timeline-copy">
                  订单、推广、日志和任务结果在同一后台中回溯，更适合商业化运营。
                </p>
              </div>
            </article>
          </div>
        </div>
      </section>

      <section class="scholar-auth__panel">
        <div class="scholar-auth__form-shell scholar-stack">
          <div class="scholar-auth__panel-head">
            <span class="scholar-badge scholar-badge--warn">管理员入口</span>
            <h2>后台登录</h2>
            <p class="scholar-lead">
              输入管理员账号和密码，进入运营控制台。
            </p>
          </div>

          <div class="scholar-auth__quickline">
            <article class="scholar-auth__quickitem">
              <span>访问级别</span>
              <strong>管理员鉴权</strong>
            </article>
            <article class="scholar-auth__quickitem">
              <span>配置方式</span>
              <strong>后台优先维护</strong>
            </article>
            <article class="scholar-auth__quickitem">
              <span>运行目标</span>
              <strong>上线运营可追踪</strong>
            </article>
          </div>

          <p class="scholar-note scholar-note--warn">
            生产环境请使用独立管理员密码，并避免继续保留默认初始化口令。
          </p>

          <form class="scholar-stack scholar-stack--compact" @submit.prevent="login">
            <label class="scholar-field">
              <span class="scholar-field__label">用户名</span>
              <input
                v-model.trim="username"
                class="scholar-input"
                autocomplete="username"
                placeholder="请输入管理员用户名"
              />
            </label>

            <label class="scholar-field">
              <span class="scholar-field__label">密码</span>
              <input
                v-model.trim="password"
                type="password"
                class="scholar-input"
                autocomplete="current-password"
                placeholder="请输入密码"
              />
            </label>

            <button class="scholar-button scholar-button--block" :disabled="loading">
              {{ loading ? "登录中..." : "登录后台" }}
            </button>
          </form>

          <p v-if="errorText" class="scholar-note scholar-note--danger">{{ errorText }}</p>

          <div class="scholar-inline-actions scholar-inline-actions--spread">
            <RouterLink class="scholar-button scholar-button--ghost" to="/login">
              返回用户登录
            </RouterLink>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"

import { adminHttp } from "../../lib/http"
import { resolveAdminRedirect } from "../../lib/redirect"
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
    router.push(resolveAdminRedirect(route.query.redirect, "/admin/dashboard"))
  } catch (error) {
    errorText.value = error.message || "登录失败"
  } finally {
    loading.value = false
  }
}
</script>
