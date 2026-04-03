<template>
  <UserShell title="积分流水" subtitle="查看所有积分变动记录" :credits="userCredits" @buy="showBuy = !showBuy">
    <section v-if="isGuest" class="rounded-2xl border border-[#d9dee4] bg-white p-5">
      <h3 class="text-base font-semibold">登录后查看积分流水</h3>
      <p class="mt-2 text-sm leading-6 text-[#556470]">积分流水仅对已登录用户展示。登录后可查看消费、退款、返佣等完整记录。</p>
      <button class="mt-4 rounded-lg bg-[#0f7a5f] px-4 py-2 text-sm text-white" @click="goLogin">
        登录后查看积分流水
      </button>
    </section>
    <section v-else class="rounded-2xl border border-[#d9dee4] bg-white p-5">
      <div class="mb-3 flex items-center justify-between gap-3">
        <h3 class="text-base font-semibold">积分明细</h3>
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex flex-wrap gap-2">
            <button
              v-for="item in quickFilters"
              :key="item.value || 'all'"
              type="button"
              :class="chipClass(activeQuickFilter, item.value)"
              @click="setQuickFilter(item.value)"
            >
              {{ item.label }}
            </button>
          </div>
          <select v-model="filterType" class="rounded-lg border border-[#ccd5dd] px-3 py-1.5 text-sm outline-none">
            <option value="">全部类型</option>
            <option value="init">初始积分</option>
            <option value="task_consume">任务消耗</option>
            <option value="task_refund">任务退回</option>
            <option value="package_pay">积分充值</option>
            <option value="referral_invite">邀请奖励</option>
            <option value="referral_bonus">邀请福利</option>
            <option value="referral_first_pay">首充奖励</option>
            <option value="referral_recurring">持续返利</option>
            <option value="admin_adjust">管理员调整</option>
          </select>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-1.5 text-sm text-[#32414f]" @click="loadPage(1)">刷新</button>
        </div>
      </div>

      <div class="mb-3 grid gap-3 rounded-xl border border-[#e1e8ee] bg-[#f8fbff] p-3 text-sm md:grid-cols-4">
        <div>
          <div class="text-xs text-[#6b7782]">本页记录数</div>
          <div class="mt-1 text-lg font-semibold">{{ rows.length }}</div>
        </div>
        <div>
          <div class="text-xs text-[#6b7782]">本页增加积分</div>
          <div class="mt-1 text-lg font-semibold text-[#106c4f]">+{{ pageIncrease }}</div>
        </div>
        <div>
          <div class="text-xs text-[#6b7782]">本页消耗积分</div>
          <div class="mt-1 text-lg font-semibold text-[#b14133]">-{{ pageCost }}</div>
        </div>
        <div>
          <div class="text-xs text-[#6b7782]">当前筛选</div>
          <div class="mt-1 text-sm font-medium text-[#31414f]">{{ currentFilterLabel }}</div>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
              <th class="px-2 py-2">类型</th>
              <th class="px-2 py-2">变动</th>
              <th class="px-2 py-2">变动前</th>
              <th class="px-2 py-2">变动后</th>
              <th class="px-2 py-2">说明</th>
              <th class="px-2 py-2">时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id" class="border-b border-[#eef2f5]">
              <td class="px-2 py-2">
                <span class="inline-flex rounded-full border border-[#d4dde5] bg-white px-2 py-1 text-xs text-[#445664]">
                  {{ mapType(row.tx_type) }}
                </span>
              </td>
              <td class="px-2 py-2">
                <span :class="row.delta >= 0 ? 'text-[#106c4f]' : 'text-[#b14133]'">
                  {{ row.delta >= 0 ? `+${row.delta}` : row.delta }}
                </span>
              </td>
              <td class="px-2 py-2">{{ row.balance_before }}</td>
              <td class="px-2 py-2">{{ row.balance_after }}</td>
              <td class="px-2 py-2">{{ row.reason || "-" }}</td>
              <td class="px-2 py-2">{{ formatTime(row.created_at) }}</td>
            </tr>
            <tr v-if="rows.length === 0">
              <td class="px-2 py-3 text-[#5b6771]" colspan="6">暂无积分记录</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="totalPages > 1" class="mt-4 flex justify-center gap-2">
        <button
          v-for="p in displayPages"
          :key="p"
          class="rounded px-3 py-1 text-sm"
          :class="p === currentPage ? 'bg-[#0f7a5f] text-white' : 'bg-[#edf2f6] text-[#344250]'"
          @click="loadPage(p)"
        >
          {{ p }}
        </button>
      </div>
    </section>
    <BuyCreditsPanel v-if="showBuy" @paid="afterPaid" />
  </UserShell>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import BuyCreditsPanel from "../../components/BuyCreditsPanel.vue"
import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { userHttp } from "../../lib/http"
import { getUserToken } from "../../lib/session"

const route = useRoute()
const router = useRouter()
const showBuy = ref(false)
const rows = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const filterType = ref("")
const activeQuickFilter = ref("")
const quickFilters = [
  { value: "", label: "全部" },
  { value: "task_consume", label: "任务消耗" },
  { value: "task_refund", label: "任务退回" },
  { value: "package_pay", label: "积分充值" },
  { value: "referral_invite", label: "邀请奖励" },
]

const { user, refreshUser } = useUserProfile()
const isGuest = computed(() => !getUserToken())
const userCredits = computed(() => {
  const value = user.value && user.value.credits
  return typeof value === "number" ? value : null
})

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const pageIncrease = computed(() =>
  rows.value.filter((row) => Number(row.delta) > 0).reduce((sum, row) => sum + Number(row.delta || 0), 0)
)
const pageCost = computed(() =>
  rows.value.filter((row) => Number(row.delta) < 0).reduce((sum, row) => sum + Math.abs(Number(row.delta || 0)), 0)
)
const currentFilterLabel = computed(() => (filterType.value ? mapType(filterType.value) : "全部类型"))

const displayPages = computed(() => {
  const tp = totalPages.value
  const cp = currentPage.value
  const pages = []
  for (let p = Math.max(1, cp - 2); p <= Math.min(tp, cp + 2); p++) {
    pages.push(p)
  }
  return pages
})

watch(filterType, (value) => {
  const matched = quickFilters.find((item) => item.value === value)
  activeQuickFilter.value = matched ? matched.value : ""
  loadPage(1)
})

onMounted(async () => {
  if (getUserToken()) {
    await refreshUser()
    await loadPage(1)
  } else {
    rows.value = []
    total.value = 0
  }
})

async function loadPage(page) {
  if (!getUserToken()) {
    rows.value = []
    total.value = 0
    return
  }
  currentPage.value = page
  const params = { page, page_size: pageSize.value }
  if (filterType.value) {
    params.tx_type = filterType.value
  }
  const data = await userHttp.get("/users/me/credit-transactions", { params })
  rows.value = data.items || []
  total.value = data.pagination?.total || 0
}

function setQuickFilter(value) {
  activeQuickFilter.value = value
  filterType.value = value
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

function chipClass(current, value) {
  const active = current === value
  if (active) {
    return "rounded-xl border border-[#0f7a5f] bg-[#e8f4ef] px-3 py-1.5 text-sm font-medium text-[#0f6c53]"
  }
  return "rounded-xl border border-[#cfd8e0] bg-white px-3 py-1.5 text-sm text-[#485864] hover:border-[#98adbb]"
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}

async function afterPaid() {
  if (getUserToken()) {
    await refreshUser()
  }
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/credits")
  router.push(`/login?redirect=${redirect}`)
}
</script>
