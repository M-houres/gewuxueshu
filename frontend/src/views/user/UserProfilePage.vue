<template>
  <UserShell title="个人中心" subtitle="账户信息与积分流水" :credits="userCredits" @buy="goBuy">
    <div class="space-y-4">
      <section v-if="isGuest" class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold">游客模式</h3>
        <p class="mt-2 text-sm leading-6 text-[#556470]">个人中心需要登录后查看。登录后可管理昵称、查看积分明细与账户信息。</p>
        <button class="mt-4 rounded-lg bg-[#0f7a5f] px-4 py-2 text-sm text-white" @click="goLogin">
          登录后进入个人中心
        </button>
      </section>

      <template v-else>
      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold">账户信息</h3>
        <div class="mt-3 grid gap-3 text-sm md:grid-cols-2">
          <div>手机号：{{ user.value?.phone || "-" }}</div>
          <div>注册时间：{{ formatTime(user.value?.created_at) }}</div>
          <div class="md:col-span-2">
            <div class="mb-1">昵称</div>
            <div class="flex gap-2">
              <input v-model.trim="nickname" class="min-w-0 flex-1 rounded-lg border border-[#ccd5dd] px-3 py-2 outline-none" />
              <button class="rounded-lg bg-[#0f7a5f] px-3 py-2 text-white" @click="saveNickname">保存昵称</button>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-base font-semibold">积分概览</h3>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="goBuy">去充值</button>
        </div>
        <div class="grid gap-3 md:grid-cols-3">
          <div class="rounded-lg bg-[#f5f8fb] px-3 py-2 text-sm">当前余额：{{ typeof userCredits === "number" ? userCredits : 0 }}</div>
          <div class="rounded-lg bg-[#f5f8fb] px-3 py-2 text-sm">累计入账：{{ summary.income }}</div>
          <div class="rounded-lg bg-[#f5f8fb] px-3 py-2 text-sm">累计支出：{{ summary.outcome }}</div>
        </div>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-base font-semibold">积分流水</h3>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadTransactions">刷新</button>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">时间</th>
                <th class="px-2 py-2">类型</th>
                <th class="px-2 py-2">变动</th>
                <th class="px-2 py-2">前余额</th>
                <th class="px-2 py-2">后余额</th>
                <th class="px-2 py-2">备注</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in txRows" :key="row.id" class="border-b border-[#eef2f5]">
                <td class="px-2 py-2">{{ formatTime(row.created_at) }}</td>
                <td class="px-2 py-2">{{ mapType(row.tx_type) }}</td>
                <td class="px-2 py-2">
                  <span :class="row.delta >= 0 ? 'text-[#106c4f]' : 'text-[#b14133]'">{{ row.delta }}</span>
                </td>
                <td class="px-2 py-2">{{ row.balance_before }}</td>
                <td class="px-2 py-2">{{ row.balance_after }}</td>
                <td class="px-2 py-2">{{ row.reason || "-" }}</td>
              </tr>
              <tr v-if="txRows.length === 0">
                <td class="px-2 py-3 text-[#5b6771]" colspan="6">暂无流水</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      </template>
    </div>
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
    task_consume: "任务消耗",
    task_refund: "任务退回",
    package_pay: "积分充值",
    referral_invite: "邀请奖励",
    referral_bonus: "邀请福利",
    referral_first_pay: "首充奖励",
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
