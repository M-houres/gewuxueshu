<template>
  <AdminShell title="订单管理" subtitle="筛选、详情与退款操作">
    <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
      <div class="mb-4 space-y-4 rounded-2xl border border-[#dee6ed] bg-[#f8fbff] p-4">
        <div class="grid gap-2 md:grid-cols-2">
          <input v-model.trim="filters.qPhone" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none" placeholder="手机号" />
          <input v-model.trim="filters.orderNo" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none" placeholder="订单号" />
        </div>
        <div>
          <div class="mb-2 text-xs font-semibold tracking-[0.08em] text-[#6b7a86]">支付方式</div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="item in providerOptions"
              :key="item.value || 'all-provider'"
              type="button"
              :class="chipClass(filters.provider, item.value)"
              @click="filters.provider = item.value"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
        <div>
          <div class="mb-2 text-xs font-semibold tracking-[0.08em] text-[#6b7a86]">订单状态</div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="item in statusOptions"
              :key="item.value || 'all-status'"
              type="button"
              :class="chipClass(filters.status, item.value)"
              @click="filters.status = item.value"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
        <div class="flex gap-2">
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadData">查询</button>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="resetFilters">重置</button>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
              <th class="px-2 py-2">订单号</th>
              <th class="px-2 py-2">用户ID</th>
              <th class="px-2 py-2">金额</th>
              <th class="px-2 py-2">积分</th>
              <th class="px-2 py-2">支付方式</th>
              <th class="px-2 py-2">状态</th>
              <th class="px-2 py-2">首充</th>
              <th class="px-2 py-2">时间</th>
              <th class="px-2 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.order_no" class="border-b border-[#eef2f5]">
              <td class="px-2 py-2">{{ row.order_no }}</td>
              <td class="px-2 py-2">{{ row.user_id }}</td>
              <td class="px-2 py-2">{{ row.amount_cny }}</td>
              <td class="px-2 py-2">{{ row.credits }}</td>
              <td class="px-2 py-2">{{ mapProvider(row.provider) }}</td>
              <td class="px-2 py-2">
                <span :class="statusClass(row.status)" class="inline-flex items-center rounded-full border px-2 py-1 text-xs">
                  {{ mapStatus(row.status) }}
                </span>
              </td>
              <td class="px-2 py-2">{{ row.is_first_pay ? "是" : "否" }}</td>
              <td class="px-2 py-2">{{ formatTime(row.created_at) }}</td>
              <td class="px-2 py-2">
                <div class="flex gap-2">
                  <button class="rounded bg-[#0f7a5f] px-2 py-1 text-xs text-white" @click="openDetail(row.order_no)">详情</button>
                  <button class="rounded bg-[#edf2f6] px-2 py-1 text-xs text-[#344250] disabled:opacity-50" :disabled="row.status !== 'paid'" @click="refund(row)">退款</button>
                </div>
              </td>
            </tr>
            <tr v-if="rows.length === 0">
              <td class="px-2 py-3 text-[#5b6771]" colspan="9">暂无订单</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="detail" class="mt-4 rounded-2xl border border-[#d9dee4] bg-white p-5 text-sm">
      <div class="mb-3 flex items-center justify-between">
        <h3 class="text-base font-semibold">订单详情 {{ detail.order_no }}</h3>
        <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="detail = null">关闭</button>
      </div>
      <div class="grid gap-2 md:grid-cols-2">
        <div>用户：{{ detail.user_id }} {{ detail.user_phone ? `(${detail.user_phone})` : "" }}</div>
        <div>金额：{{ detail.amount_cny }}</div>
        <div>积分：{{ detail.credits }}</div>
        <div>支付方式：{{ mapProvider(detail.provider) }}</div>
        <div>状态：{{ mapStatus(detail.status) }}</div>
        <div>首充：{{ detail.is_first_pay ? "是" : "否" }}</div>
        <div>下单时间：{{ formatTime(detail.created_at) }}</div>
        <div>更新时间：{{ formatTime(detail.updated_at) }}</div>
      </div>
    </section>
  </AdminShell>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue"

import AdminShell from "../../components/AdminShell.vue"
import { adminHttp } from "../../lib/http"

const rows = ref([])
const detail = ref(null)
const filters = reactive({
  qPhone: "",
  orderNo: "",
  provider: "",
  status: "",
})
const providerOptions = [
  { value: "", label: "全部" },
  { value: "mock", label: "测试支付" },
  { value: "wechat", label: "微信支付" },
  { value: "alipay", label: "支付宝" },
]
const statusOptions = [
  { value: "", label: "全部" },
  { value: "paid", label: "已支付" },
  { value: "created", label: "待支付" },
  { value: "closed", label: "已关闭" },
  { value: "refunded", label: "已退款" },
]

onMounted(loadData)

async function loadData() {
  const params = {
    page: 1,
    page_size: 100,
    q_phone: filters.qPhone || undefined,
    order_no: filters.orderNo || undefined,
    provider: filters.provider || undefined,
    status: filters.status || undefined,
  }
  const data = await adminHttp.get("/admin/orders", { params })
  rows.value = data.items || []
}

function resetFilters() {
  filters.qPhone = ""
  filters.orderNo = ""
  filters.provider = ""
  filters.status = ""
  loadData()
}

async function openDetail(orderNo) {
  detail.value = await adminHttp.get(`/admin/orders/${orderNo}/detail`)
}

async function refund(row) {
  const confirmed = window.confirm(`确认退款订单 ${row.order_no} 吗？`)
  if (!confirmed) {
    return
  }
  await adminHttp.post(`/admin/orders/${row.order_no}/refund`)
  await loadData()
  if (detail.value?.order_no === row.order_no) {
    await openDetail(row.order_no)
  }
}

function mapProvider(provider) {
  const mapping = {
    mock: "测试支付",
    wechat: "微信支付",
    alipay: "支付宝",
  }
  return mapping[provider] || provider
}

function mapStatus(status) {
  const mapping = {
    paid: "已支付",
    created: "待支付",
    closed: "已关闭",
    refunded: "已退款",
  }
  return mapping[status] || status
}

function statusClass(status) {
  if (status === "paid") return "border-[#b8e7d5] bg-[#dbf5ea] text-[#106c4f]"
  if (status === "refunded") return "border-[#f4c5c1] bg-[#ffe1df] text-[#9c2d2a]"
  if (status === "closed") return "border-[#d3dce4] bg-[#eef3f8] text-[#5a6874]"
  return "border-[#f2dfb3] bg-[#fff2d8] text-[#8a5a10]"
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
</script>
