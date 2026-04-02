<template>
  <AdminShell title="用户管理" subtitle="查询用户与积分调整">
    <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <input v-model.trim="keyword" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none focus:border-[#0f7a5f]" placeholder="按手机号搜索" />
        <div class="flex flex-wrap gap-2">
          <button
            v-for="item in statusFilters"
            :key="item.value || 'all'"
            type="button"
            :class="chipClass(activeStatusFilter, item.value)"
            @click="activeStatusFilter = item.value"
          >
            {{ item.label }}
          </button>
        </div>
        <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadData">查询</button>
      </div>
      <div class="mb-3 grid gap-3 rounded-xl border border-[#e1e8ee] bg-[#f8fbff] p-3 text-sm md:grid-cols-3">
        <div>
          <div class="text-xs text-[#6b7782]">当前加载用户</div>
          <div class="mt-1 text-lg font-semibold">{{ rows.length }}</div>
        </div>
        <div>
          <div class="text-xs text-[#6b7782]">正常用户</div>
          <div class="mt-1 text-lg font-semibold text-[#106c4f]">{{ activeCount }}</div>
        </div>
        <div>
          <div class="text-xs text-[#6b7782]">封禁用户</div>
          <div class="mt-1 text-lg font-semibold text-[#b14133]">{{ bannedCount }}</div>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
              <th class="px-2 py-2">用户ID</th>
              <th class="px-2 py-2">手机号</th>
              <th class="px-2 py-2">昵称</th>
              <th class="px-2 py-2">积分</th>
              <th class="px-2 py-2">状态</th>
              <th class="px-2 py-2">创建时间</th>
              <th class="px-2 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in displayRows" :key="row.id" class="border-b border-[#eef2f5]">
              <td class="px-2 py-2">{{ row.id }}</td>
              <td class="px-2 py-2">{{ row.phone }}</td>
              <td class="px-2 py-2">{{ row.nickname }}</td>
              <td class="px-2 py-2">{{ row.credits }}</td>
              <td class="px-2 py-2">
                <span
                  :class="row.is_banned ? 'border-[#f4c5c1] bg-[#ffe1df] text-[#9c2d2a]' : 'border-[#cfe6db] bg-[#e8f4ef] text-[#106c4f]'"
                  class="inline-flex rounded-full border px-2 py-1 text-xs"
                >
                  {{ row.is_banned ? "已封禁" : "正常" }}
                </span>
              </td>
              <td class="px-2 py-2">{{ formatTime(row.created_at) }}</td>
              <td class="px-2 py-2">
                <div class="flex gap-2">
                  <button class="rounded bg-[#0f7a5f] px-2 py-1 text-xs text-white" @click="goDetail(row)">查看详情</button>
                  <button class="rounded bg-[#edf2f6] px-2 py-1 text-xs text-[#344250]" @click="toggleBan(row)">
                    {{ row.is_banned ? "解封" : "封禁" }}
                  </button>
                  <button class="rounded bg-[#0f7a5f] px-2 py-1 text-xs text-white" @click="openAdjust(row)">调整积分</button>
                </div>
              </td>
            </tr>
            <tr v-if="displayRows.length === 0">
              <td class="px-2 py-3 text-[#5b6771]" colspan="7">暂无用户数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="editing" class="mt-4 rounded-2xl border border-[#d9dee4] bg-white p-5">
      <h3 class="text-base font-semibold">调整积分：{{ editing.phone }}</h3>
      <div class="mt-3 grid gap-3 md:grid-cols-3">
        <input v-model.number="delta" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none focus:border-[#0f7a5f]" placeholder="输入正负积分" />
        <input v-model.trim="reason" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none focus:border-[#0f7a5f]" placeholder="调整原因" />
        <button class="rounded-lg bg-[#0f7a5f] px-3 py-2 text-sm text-white" @click="submitAdjust">确认调整</button>
      </div>
      <p v-if="hintText" class="mt-2 text-sm text-[#106c4f]">{{ hintText }}</p>
      <p v-if="errorText" class="mt-2 text-sm text-[#af3f33]">{{ errorText }}</p>
    </section>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import AdminShell from "../../components/AdminShell.vue"
import { adminHttp } from "../../lib/http"

const router = useRouter()
const rows = ref([])
const keyword = ref("")
const activeStatusFilter = ref("")
const editing = ref(null)
const delta = ref(0)
const reason = ref("")
const hintText = ref("")
const errorText = ref("")
const statusFilters = [
  { value: "", label: "全部状态" },
  { value: "active", label: "正常" },
  { value: "banned", label: "已封禁" },
]
const displayRows = computed(() => {
  if (!activeStatusFilter.value) return rows.value
  if (activeStatusFilter.value === "active") return rows.value.filter((row) => !row.is_banned)
  return rows.value.filter((row) => row.is_banned)
})
const activeCount = computed(() => rows.value.filter((row) => !row.is_banned).length)
const bannedCount = computed(() => rows.value.filter((row) => row.is_banned).length)

onMounted(loadData)

async function loadData() {
  const data = await adminHttp.get("/admin/users", {
    params: { page: 1, page_size: 50, q: keyword.value || undefined },
  })
  rows.value = data.items || []
}

function openAdjust(row) {
  editing.value = row
  delta.value = 0
  reason.value = ""
  hintText.value = ""
  errorText.value = ""
}

async function submitAdjust() {
  if (!editing.value) return
  if (!delta.value) {
    errorText.value = "调整值不能为0"
    return
  }
  if (!reason.value) {
    errorText.value = "请输入调整原因"
    return
  }
  errorText.value = ""
  const data = await adminHttp.post(`/admin/users/${editing.value.id}/adjust-credits`, {
    delta: delta.value,
    reason: reason.value,
  })
  hintText.value = `已调整成功，当前积分 ${data.credits}`
  await loadData()
}

function goDetail(row) {
  router.push(`/admin/users/${row.id}`)
}

async function toggleBan(row) {
  const target = !row.is_banned
  const confirmed = window.confirm(target ? "确认封禁该用户吗？" : "确认解封该用户吗？")
  if (!confirmed) {
    return
  }
  await adminHttp.post(`/admin/users/${row.id}/ban`, { is_banned: target })
  await loadData()
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}

function chipClass(current, value) {
  const active = current === value
  if (active) {
    return "rounded-xl border border-[#0f7a5f] bg-[#e8f4ef] px-3 py-1.5 text-sm font-medium text-[#0f6c53]"
  }
  return "rounded-xl border border-[#cfd8e0] bg-white px-3 py-1.5 text-sm text-[#485864] hover:border-[#98adbb]"
}
</script>
