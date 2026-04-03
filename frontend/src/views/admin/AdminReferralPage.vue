<template>
  <AdminShell title="推广管理" subtitle="规则配置、奖励流水与异常注册。">
    <div class="space-y-4">
      <section class="grid gap-4 md:grid-cols-4">
        <article class="rounded-2xl border border-[#d9dee4] bg-white p-4">
          <div class="text-xs text-[#5b6771]">邀请关系总数</div>
          <div class="mt-2 text-2xl font-semibold">{{ stats.total_relations || 0 }}</div>
        </article>
        <article class="rounded-2xl border border-[#d9dee4] bg-white p-4">
          <div class="text-xs text-[#5b6771]">推广积分总发放</div>
          <div class="mt-2 text-2xl font-semibold">{{ stats.total_reward_credits || 0 }}</div>
        </article>
        <article class="rounded-2xl border border-[#d9dee4] bg-white p-4">
          <div class="text-xs text-[#5b6771]">今日新增邀请</div>
          <div class="mt-2 text-2xl font-semibold">{{ stats.today_new_relations || 0 }}</div>
        </article>
        <article class="rounded-2xl border border-[#d9dee4] bg-white p-4">
          <div class="text-xs text-[#5b6771]">Top 推广者数量</div>
          <div class="mt-2 text-2xl font-semibold">{{ (stats.top10 || []).length }}</div>
        </article>
      </section>

      <section v-if="canManageReferrals" class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold">推广规则配置</h3>
        <div class="mt-2 rounded-xl border border-[#e1e8ee] bg-[#f8fbff] p-3 text-sm leading-6 text-[#50606c]">
          运营只需配置 5 个字段：注册奖励、返佣比例、同 IP 24 小时注册上限。
        </div>
        <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <label class="space-y-1 text-sm">
            <span>邀请人注册奖励（积分）</span>
            <input v-model.number="form.register_inviter_credits" class="w-full rounded-lg border border-[#ccd5dd] px-3 py-2 outline-none focus:border-[#0f7a5f]" />
          </label>
          <label class="space-y-1 text-sm">
            <span>被邀请人注册福利（积分）</span>
            <input v-model.number="form.register_invitee_bonus" class="w-full rounded-lg border border-[#ccd5dd] px-3 py-2 outline-none focus:border-[#0f7a5f]" />
          </label>
          <label class="space-y-1 text-sm">
            <span>首充返佣比例（%）</span>
            <input v-model.number="firstPayPct" class="w-full rounded-lg border border-[#ccd5dd] px-3 py-2 outline-none focus:border-[#0f7a5f]" />
          </label>
          <label class="space-y-1 text-sm">
            <span>持续返利比例（%）</span>
            <input v-model.number="recurringPct" class="w-full rounded-lg border border-[#ccd5dd] px-3 py-2 outline-none focus:border-[#0f7a5f]" />
          </label>
          <label class="space-y-1 text-sm">
            <span>同IP 24小时注册上限</span>
            <input v-model.number="form.ip_limit_24h" class="w-full rounded-lg border border-[#ccd5dd] px-3 py-2 outline-none focus:border-[#0f7a5f]" />
          </label>
        </div>
        <button class="mt-3 rounded-lg bg-[#0f7a5f] px-3 py-2 text-sm text-white" @click="saveConfig">保存配置</button>
        <p v-if="hintText" class="mt-2 text-sm text-[#106c4f]">{{ hintText }}</p>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold">奖励发放记录</h3>
        <div class="mt-3 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">ID</th>
                <th class="px-2 py-2">邀请人</th>
                <th class="px-2 py-2">被邀请人</th>
                <th class="px-2 py-2">类型</th>
                <th class="px-2 py-2">积分</th>
                <th class="px-2 py-2">状态</th>
                <th class="px-2 py-2">重试</th>
                <th class="px-2 py-2">时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rewards" :key="row.id" class="border-b border-[#eef2f5]">
                <td class="px-2 py-2">{{ row.id }}</td>
                <td class="px-2 py-2">{{ row.inviter_id }}</td>
                <td class="px-2 py-2">{{ row.invitee_id }}</td>
                <td class="px-2 py-2">{{ mapRewardType(row.reward_type) }}</td>
                <td class="px-2 py-2">{{ row.credits }}</td>
                <td class="px-2 py-2">
                  <span class="rounded-full bg-[#f2f6f9] px-2 py-1 text-xs text-[#44525d]">{{ mapRewardStatus(row.status) }}</span>
                </td>
                <td class="px-2 py-2">
                  <button v-if="canManageReferrals" class="rounded bg-[#0f7a5f] px-2 py-1 text-xs text-white" @click="retry(row)">重试</button>
                  <span v-else>-</span>
                </td>
                <td class="px-2 py-2">{{ formatTime(row.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold">异常注册列表</h3>
        <div class="mt-3 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">记录ID</th>
                <th class="px-2 py-2">手机号</th>
                <th class="px-2 py-2">IP</th>
                <th class="px-2 py-2">原因</th>
                <th class="px-2 py-2">时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in suspiciousRows" :key="row.id" class="border-b border-[#eef2f5]">
                <td class="px-2 py-2">{{ row.id }}</td>
                <td class="px-2 py-2">{{ row.phone }}</td>
                <td class="px-2 py-2">{{ row.ip }}</td>
                <td class="px-2 py-2">{{ row.reason }}</td>
                <td class="px-2 py-2">{{ formatTime(row.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"

import AdminShell from "../../components/AdminShell.vue"
import { adminHttp } from "../../lib/http"
import { adminHasPermission } from "../../lib/session"

const stats = ref({})
const rewards = ref([])
const suspiciousRows = ref([])
const hintText = ref("")
const firstPayPct = ref(10)
const recurringPct = ref(5)
const form = ref({
  register_inviter_credits: 500,
  register_invitee_bonus: 500,
  first_pay_ratio: 0.1,
  recurring_ratio: 0.05,
  ip_limit_24h: 3,
})

const canManageReferrals = computed(() => adminHasPermission("referrals:manage"))

onMounted(loadAll)

async function loadAll() {
  const jobs = [
    adminHttp.get("/admin/referrals/stats"),
    adminHttp.get("/admin/referrals/rewards", { params: { page: 1, page_size: 50 } }),
    adminHttp.get("/admin/referrals/suspicious", { params: { page: 1, page_size: 50 } }),
  ]
  if (canManageReferrals.value) {
    jobs.push(adminHttp.get("/admin/referrals/config"))
  }

  const [statsData, rewardData, suspiciousData, cfgData] = await Promise.all(jobs)
  stats.value = statsData
  rewards.value = rewardData.items || []
  suspiciousRows.value = suspiciousData.items || []

  if (cfgData) {
    form.value = { ...form.value, ...cfgData }
    firstPayPct.value = Number((form.value.first_pay_ratio || 0) * 100)
    recurringPct.value = Number((form.value.recurring_ratio || 0) * 100)
  }
}

async function saveConfig() {
  const confirmed = window.confirm("确认保存推广规则配置吗？")
  if (!confirmed) {
    return
  }
  await adminHttp.post("/admin/referrals/config", {
    ...form.value,
    first_pay_ratio: Number(firstPayPct.value || 0) / 100,
    recurring_ratio: Number(recurringPct.value || 0) / 100,
  })
  hintText.value = "配置已保存"
  await loadAll()
}

async function retry(row) {
  await adminHttp.post(`/admin/referrals/rewards/${row.id}/retry`)
  hintText.value = `奖励记录 ${row.id} 已加入重试队列`
}

function mapRewardType(type) {
  const map = {
    register_invite: "邀请注册奖励",
    register_bonus: "被邀请注册福利",
    first_pay: "首充返佣",
    recurring_pay: "持续返利",
  }
  return map[type] || type || "-"
}

function mapRewardStatus(status) {
  const map = {
    sent: "已发放",
    pending: "待发放",
    failed: "失败",
  }
  return map[status] || status || "-"
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}
</script>
