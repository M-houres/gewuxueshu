<template>
  <UserShell title="个人中心" subtitle="维护账号信息、积分总览与积分流水。" :credits="userCredits" @buy="goBuy">
    <section v-if="isGuest" class="scholar-panel scholar-panel--soft">
      <div class="scholar-panel__body">
        <div class="scholar-kicker">Guest Mode</div>
        <h3 class="scholar-subtitle">登录后查看个人资料</h3>
        <p class="scholar-lead">
          个人中心仅在登录后开放，可维护昵称、查看积分变化和账户基本信息。
        </p>
        <button class="scholar-button" type="button" style="margin-top: 18px" @click="goLogin">
          登录后进入个人中心
        </button>
      </div>
    </section>

    <template v-else>
      <section class="scholar-grid scholar-grid--halves">
        <article class="scholar-panel scholar-panel--soft">
          <div class="scholar-panel__body">
            <div class="scholar-kicker">Account</div>
            <h3 class="scholar-subtitle">账户信息</h3>
            <div class="scholar-stack" style="margin-top: 18px">
              <div class="scholar-note">手机号：{{ user.value?.phone || "-" }}</div>
              <div class="scholar-note">注册时间：{{ formatTime(user.value?.created_at) }}</div>
              <label class="scholar-field">
                <span class="scholar-field__label">昵称</span>
                <div class="scholar-inline-actions">
                  <input v-model.trim="nickname" class="scholar-input" style="flex: 1" />
                  <button class="scholar-button" type="button" @click="saveNickname">保存昵称</button>
                </div>
              </label>
            </div>
          </div>
        </article>

        <article class="scholar-panel scholar-panel--soft">
          <div class="scholar-panel__body">
            <div class="scholar-kicker">Credits Overview</div>
            <h3 class="scholar-subtitle">积分概览</h3>
            <div class="scholar-grid md:grid-cols-3" style="margin-top: 18px">
              <div class="scholar-stat">
                <div class="scholar-stat__label">当前余额</div>
                <div class="scholar-stat__value" style="font-size: 26px">{{ typeof userCredits === "number" ? userCredits : 0 }}</div>
              </div>
              <div class="scholar-stat">
                <div class="scholar-stat__label">累计入账</div>
                <div class="scholar-stat__value" style="font-size: 26px">{{ summary.income }}</div>
              </div>
              <div class="scholar-stat">
                <div class="scholar-stat__label">累计支出</div>
                <div class="scholar-stat__value" style="font-size: 26px">{{ summary.outcome }}</div>
              </div>
            </div>
            <div class="scholar-inline-actions" style="margin-top: 18px">
              <button class="scholar-button" type="button" @click="goBuy">去充值</button>
            </div>
          </div>
        </article>
      </section>

      <section class="scholar-panel">
        <div class="scholar-panel__header">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="scholar-kicker">Credit Transactions</div>
              <h3 class="scholar-subtitle">积分流水</h3>
            </div>
            <button class="scholar-button scholar-button--secondary" type="button" @click="loadTransactions">
              刷新
            </button>
          </div>
        </div>

        <div class="scholar-panel__body">
          <div class="overflow-x-auto">
            <table class="scholar-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>类型</th>
                  <th>变化</th>
                  <th>前余额</th>
                  <th>后余额</th>
                  <th>备注</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in txRows" :key="row.id">
                  <td>{{ formatTime(row.created_at) }}</td>
                  <td>{{ mapType(row.tx_type) }}</td>
                  <td :style="{ color: row.delta >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }">
                    {{ row.delta }}
                  </td>
                  <td>{{ row.balance_before }}</td>
                  <td>{{ row.balance_after }}</td>
                  <td>{{ row.reason || "-" }}</td>
                </tr>
                <tr v-if="txRows.length === 0">
                  <td colspan="6">
                    <div class="scholar-empty">暂无流水</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </template>
  </UserShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { userHttp } from "../../lib/http"
import { ensureUserLogin } from "../../lib/requireLogin"
import { getUserToken } from "../../lib/session"

const router = useRouter()
const route = useRoute()
const { user, refreshUser } = useUserProfile()
const nickname = ref("")
const txRows = ref([])
const summary = reactive({ income: 0, outcome: 0 })
const isGuest = computed(() => !getUserToken())

const userCredits = computed(() => {
  const value = user.value && user.value.credits
  return typeof value === "number" ? value : null
})

onMounted(async () => {
  if (getUserToken()) {
    await refreshUser()
  }
  nickname.value = user.value?.nickname || ""
  if (getUserToken()) {
    await loadTransactions()
  }
})

async function loadTransactions() {
  if (!getUserToken()) {
    txRows.value = []
    summary.income = 0
    summary.outcome = 0
    return
  }
  const data = await userHttp.get("/users/me/credit-transactions", { params: { page: 1, page_size: 100 } })
  txRows.value = data.items || []
  let income = 0
  let outcome = 0
  for (const row of txRows.value) {
    if (row.delta >= 0) income += row.delta
    else outcome += Math.abs(row.delta)
  }
  summary.income = income
  summary.outcome = outcome
}

async function saveNickname() {
  if (!ensureUserLogin(router, { fullPath: "/app/profile" }, "/app/profile")) {
    return
  }
  if (!nickname.value) return
  await userHttp.patch("/users/me", { nickname: nickname.value })
  await refreshUser()
}

function mapType(type) {
  const map = {
    init: "初始积分",
    task_consume: "任务消费",
    task_refund: "任务退款",
    package_pay: "积分充值",
    referral_invite: "邀请奖励",
    referral_bonus: "被邀请福利",
    referral_first_pay: "首充返佣",
    referral_recurring: "持续返利",
    admin_adjust: "管理员调整",
  }
  return map[type] || type
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}

function goBuy() {
  router.push("/app/buy")
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/profile")
  router.push(`/login?redirect=${redirect}`)
}
</script>
