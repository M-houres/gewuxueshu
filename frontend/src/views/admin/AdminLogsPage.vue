<template>
  <AdminShell title="系统日志" subtitle="模式切换日志与大模型异常日志">
    <div class="space-y-4">
      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="flex flex-wrap gap-2">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="rounded-lg px-3 py-2 text-sm"
            :class="activeTab === tab.key ? 'bg-[#0f7a5f] text-white' : 'bg-[#edf2f6] text-[#344250]'"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </section>

      <section v-if="activeTab === 'switch'" class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-base font-semibold">模式切换日志</h3>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadSwitchLogs">刷新</button>
        </div>
        <div class="mb-3 rounded-xl border border-[#e1e8ee] bg-[#f8fbff] px-3 py-2 text-sm text-[#4f5f6b]">
          共 {{ switchRows.length }} 条切换记录
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">时间</th>
                <th class="px-2 py-2">切换前</th>
                <th class="px-2 py-2">切换后</th>
                <th class="px-2 py-2">原因</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in switchRows" :key="row.id" class="border-b border-[#eef2f5]">
                <td class="px-2 py-2">{{ formatTime(row.created_at) }}</td>
                <td class="px-2 py-2">{{ row.from_mode }}</td>
                <td class="px-2 py-2">{{ row.to_mode }}</td>
                <td class="px-2 py-2">{{ row.reason }}</td>
              </tr>
              <tr v-if="switchRows.length === 0">
                <td class="px-2 py-3 text-[#5b6771]" colspan="4">暂无切换日志</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-else class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="mb-3 flex items-center justify-between gap-3">
          <h3 class="text-base font-semibold">大模型异常日志</h3>
          <div class="flex flex-wrap items-center gap-2">
            <select v-model="errorTypeFilter" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none">
              <option value="">全部错误类型</option>
              <option v-for="t in errorTypes" :key="t" :value="t">{{ t }}</option>
            </select>
            <input
              v-model.trim="keyword"
              class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none"
              placeholder="按错误详情检索"
            />
            <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadLlmErrorLogs">刷新</button>
            <button class="rounded-lg bg-[#0f7a5f] px-3 py-2 text-sm text-white" @click="exportCsv">导出CSV</button>
          </div>
        </div>
        <div class="mb-3 grid gap-3 rounded-xl border border-[#e1e8ee] bg-[#f8fbff] p-3 text-sm md:grid-cols-3">
          <div>
            <div class="text-xs text-[#6b7782]">异常总数</div>
            <div class="mt-1 text-lg font-semibold">{{ llmRows.length }}</div>
          </div>
          <div>
            <div class="text-xs text-[#6b7782]">触发降级</div>
            <div class="mt-1 text-lg font-semibold text-[#b14133]">{{ downgradeCount }}</div>
          </div>
          <div>
            <div class="text-xs text-[#6b7782]">当前展示</div>
            <div class="mt-1 text-lg font-semibold text-[#106c4f]">{{ filteredLlmRows.length }}</div>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">时间</th>
                <th class="px-2 py-2">任务ID</th>
                <th class="px-2 py-2">错误类型</th>
                <th class="px-2 py-2">错误详情</th>
                <th class="px-2 py-2">触发降级</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredLlmRows" :key="row.id" class="border-b border-[#eef2f5]">
                <td class="px-2 py-2">{{ formatTime(row.created_at) }}</td>
                <td class="px-2 py-2">{{ row.task_id || "-" }}</td>
                <td class="px-2 py-2">
                  <span class="inline-flex rounded-full border border-[#d4dde5] bg-white px-2 py-1 text-xs text-[#445664]">
                    {{ row.error_type }}
                  </span>
                </td>
                <td class="max-w-xl px-2 py-2">{{ row.error_detail }}</td>
                <td class="px-2 py-2">
                  <span
                    :class="row.trigger_downgrade ? 'border-[#f4c5c1] bg-[#ffe1df] text-[#9c2d2a]' : 'border-[#cfe6db] bg-[#e8f4ef] text-[#106c4f]'"
                    class="inline-flex rounded-full border px-2 py-1 text-xs"
                  >
                    {{ row.trigger_downgrade ? "是" : "否" }}
                  </span>
                </td>
              </tr>
              <tr v-if="filteredLlmRows.length === 0">
                <td class="px-2 py-3 text-[#5b6771]" colspan="5">暂无异常日志</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"

import AdminShell from "../../components/AdminShell.vue"
import { adminHttp } from "../../lib/http"

const tabs = [
  { key: "switch", label: "模式切换日志" },
  { key: "llm", label: "大模型异常日志" },
]

const activeTab = ref("switch")
const switchRows = ref([])
const llmRows = ref([])
const errorTypeFilter = ref("")
const keyword = ref("")

const errorTypes = computed(() => {
  const set = new Set(llmRows.value.map((r) => r.error_type).filter(Boolean))
  return Array.from(set)
})
const filteredLlmRows = computed(() => {
  const key = keyword.value.trim().toLowerCase()
  if (!key) {
    return llmRows.value
  }
  return llmRows.value.filter((row) => String(row.error_detail || "").toLowerCase().includes(key))
})
const downgradeCount = computed(() => llmRows.value.filter((row) => Boolean(row.trigger_downgrade)).length)

watch(errorTypeFilter, () => {
  loadLlmErrorLogs()
})

onMounted(async () => {
  await Promise.all([loadSwitchLogs(), loadLlmErrorLogs()])
})

async function loadSwitchLogs() {
  const data = await adminHttp.get("/admin/switch/logs", { params: { page: 1, page_size: 100 } })
  switchRows.value = data.items || []
}

async function loadLlmErrorLogs() {
  const params = { page: 1, page_size: 100 }
  if (errorTypeFilter.value) {
    params.error_type = errorTypeFilter.value
  }
  const data = await adminHttp.get("/admin/llm-error-logs", { params })
  llmRows.value = data.items || []
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}

function exportCsv() {
  const header = ["time", "task_id", "error_type", "error_detail", "trigger_downgrade"]
  const lines = filteredLlmRows.value.map((row) => {
    const cells = [
      formatTime(row.created_at),
      row.task_id || "",
      row.error_type || "",
      String(row.error_detail || "").replace(/\"/g, '""'),
      row.trigger_downgrade ? "1" : "0",
    ]
    return cells.map((c) => `"${c}"`).join(",")
  })
  const csv = [header.join(","), ...lines].join("\n")
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `llm_error_logs_${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
