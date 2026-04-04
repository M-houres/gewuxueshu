<template>
  <AdminShell title="算法包与策略" subtitle="运营只维护 9 宫格策略与激活算法包，用户侧不暴露处理模式。">
    <div class="space-y-4">
      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h3 class="text-base font-semibold text-[#1f2d3a]">算法包操作</h3>
          <div class="flex flex-wrap items-center gap-2">
            <button
              v-if="canManageAlgo"
              class="rounded-lg border border-[#0f7a5f] bg-[#e8f4ef] px-3 py-2 text-sm text-[#0f6c53] hover:border-[#0d5f49] disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="bootstrapping"
              @click="bootstrapBuiltinPackages"
            >
              {{ bootstrapping ? "初始化中..." : "一键初始化 9 个标准算法包" }}
            </button>
            <button
              class="rounded-lg border border-[#cbd5de] bg-white px-3 py-2 text-sm text-[#344250] hover:border-[#8ca2b2] disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="downloadingGuide"
              @click="downloadGuide"
            >
              {{ downloadingGuide ? "下载中..." : "下载算法包编写规范" }}
            </button>
          </div>
        </div>

        <div class="mt-3 space-y-4 rounded-2xl border border-[#dee6ed] bg-[#f8fbff] p-4">
          <div>
            <div class="mb-2 text-xs font-semibold tracking-[0.08em] text-[#6b7a86]">选择平台</div>
            <div class="grid gap-2 md:grid-cols-3">
              <button
                v-for="item in platformOptions"
                :key="item.value"
                type="button"
                :class="selectCardClass(uploadForm.platform, item.value)"
                @click="uploadForm.platform = item.value"
              >
                <div class="text-sm font-semibold">{{ item.label }}</div>
              </button>
            </div>
          </div>

          <div>
            <div class="mb-2 text-xs font-semibold tracking-[0.08em] text-[#6b7a86]">功能类型</div>
            <div class="grid gap-2 md:grid-cols-3">
              <button
                v-for="item in functionTypeOptions"
                :key="item.value"
                type="button"
                :class="selectCardClass(uploadForm.function_type, item.value)"
                @click="uploadForm.function_type = item.value"
              >
                <div class="text-sm font-semibold">{{ item.label }}</div>
              </button>
            </div>
          </div>

          <div class="rounded-xl bg-[#eef4f9] px-3 py-2 text-xs text-[#4c5d69]">
            当前选择：{{ mapPlatform(uploadForm.platform) }} / {{ mapFunctionType(uploadForm.function_type) }}
          </div>
        </div>

        <div v-if="canManageAlgo" class="mt-3 grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-center">
          <input
            type="file"
            accept=".zip,application/zip"
            class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none focus:border-[#0f7a5f]"
            @change="onFileChange"
          />
          <label class="inline-flex items-center gap-2 text-sm text-[#42505c]">
            <input v-model="activateAfterUpload" type="checkbox" class="h-4 w-4 rounded border-[#c7d0d8]" />
            上传后自动激活
          </label>
          <button
            class="rounded-lg bg-[#0f7a5f] px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="uploading || !selectedFile"
            @click="uploadPackage"
          >
            {{ uploading ? "上传中..." : "上传" }}
          </button>
        </div>

        <p v-else class="mt-3 rounded-xl border border-[#dce4eb] bg-[#f8fbff] px-3 py-2 text-sm text-[#4f5d69]">
          当前账号只有查看权限，如需上传或切换算法包，请联系超级管理员授权。
        </p>

        <p v-if="hintText" class="mt-3 text-sm text-[#106c4f]">{{ hintText }}</p>
        <p v-if="errorText" class="mt-3 text-sm text-[#af3f33]">{{ errorText }}</p>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h3 class="text-base font-semibold text-[#1f2d3a]">处理策略矩阵（9 宫格）</h3>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadStrategies">刷新</button>
        </div>
        <p class="mb-3 rounded-xl border border-[#dde6ee] bg-[#f8fbff] px-3 py-2 text-xs text-[#4f5d69]">
          每个“平台 × 功能”独立配置：处理模式、是否启用、超时时间。用户端不会看到这些内部策略。
        </p>

        <div class="grid gap-3 md:grid-cols-3">
          <article
            v-for="cell in strategyCards"
            :key="`${cell.task_type}:${cell.platform}`"
            class="rounded-xl border border-[#d9e2eb] bg-[#fbfdff] p-3"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="text-sm font-semibold text-[#263442]">
                {{ mapStrategyPlatform(cell.platform) }} · {{ mapFunctionType(cell.task_type) }}
              </div>
              <span class="rounded-full bg-[#eef3f8] px-2 py-0.5 text-[11px] text-[#5d6a76]">
                {{ cell.is_enabled ? "已启用" : "已停用" }}
              </span>
            </div>

            <div class="mt-2 text-xs text-[#64717d]">
              激活算法包：{{ cell.active_package?.name || "-" }} {{ cell.active_package?.version || "" }}
            </div>

            <div class="mt-3 flex gap-2">
              <button
                type="button"
                class="flex-1 rounded-lg border px-2 py-1.5 text-xs"
                :class="
                  cell.process_mode === 'algo_only'
                    ? 'border-[#0f7a5f] bg-[#e8f4ef] text-[#0f6c53]'
                    : 'border-[#cad4de] bg-white text-[#4c5b68]'
                "
                :disabled="!canManageAlgo"
                @click="cell.process_mode = 'algo_only'"
              >
                算法包
              </button>
              <button
                type="button"
                class="flex-1 rounded-lg border px-2 py-1.5 text-xs"
                :class="
                  cell.process_mode === 'algo_llm'
                    ? 'border-[#0f7a5f] bg-[#e8f4ef] text-[#0f6c53]'
                    : 'border-[#cad4de] bg-white text-[#4c5b68]'
                "
                :disabled="!canManageAlgo"
                @click="cell.process_mode = 'algo_llm'"
              >
                算法包+大模型
              </button>
            </div>

            <div class="mt-3 flex items-center justify-between gap-2">
              <label class="inline-flex items-center gap-2 text-xs text-[#4e5d69]">
                <input v-model="cell.is_enabled" :disabled="!canManageAlgo" type="checkbox" class="h-4 w-4 rounded border-[#c7d0d8]" />
                对用户开放
              </label>
              <select
                v-model.number="cell.timeout_sec"
                :disabled="!canManageAlgo"
                class="rounded-md border border-[#cfd8e0] bg-white px-2 py-1 text-xs text-[#3f4d58]"
              >
                <option :value="180">180 秒</option>
                <option :value="300">300 秒</option>
                <option :value="600">600 秒</option>
                <option :value="900">900 秒</option>
              </select>
            </div>

            <button
              type="button"
              class="mt-3 w-full rounded-lg bg-[#0f7a5f] px-3 py-1.5 text-xs text-white disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="savingStrategyKey === `${cell.task_type}:${cell.platform}` || !canManageAlgo"
              @click="saveStrategy(cell)"
            >
              {{ savingStrategyKey === `${cell.task_type}:${cell.platform}` ? "保存中..." : "保存策略" }}
            </button>
          </article>
        </div>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold text-[#1f2d3a]">槽位当前版本</h3>
        <div class="mt-3 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">平台</th>
                <th class="px-2 py-2">功能类型</th>
                <th class="px-2 py-2">当前包名</th>
                <th class="px-2 py-2">当前版本</th>
                <th class="px-2 py-2">Smoke</th>
                <th class="px-2 py-2">上传时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="slot in slots" :key="`${slot.platform}:${slot.function_type}`" class="border-b border-[#eef2f5]">
                <td class="px-2 py-2">{{ mapPlatform(slot.platform) }}</td>
                <td class="px-2 py-2">{{ mapFunctionType(slot.function_type) }}</td>
                <td class="px-2 py-2">{{ slot.active_name || "-" }}</td>
                <td class="px-2 py-2">{{ slot.active_version || "-" }}</td>
                <td class="px-2 py-2">{{ slot.smoke_status || "-" }}</td>
                <td class="px-2 py-2">{{ formatTime(slot.uploaded_at) }}</td>
              </tr>
              <tr v-if="slots.length === 0">
                <td colspan="6" class="px-2 py-4 text-center text-[#6b7782]">暂无槽位数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-base font-semibold text-[#1f2d3a]">已上传算法包</h3>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadPackages">刷新</button>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">名称</th>
                <th class="px-2 py-2">平台</th>
                <th class="px-2 py-2">功能类型</th>
                <th class="px-2 py-2">版本</th>
                <th class="px-2 py-2">入口</th>
                <th class="px-2 py-2">Smoke</th>
                <th class="px-2 py-2">激活开关</th>
                <th class="px-2 py-2">上传时间</th>
                <th class="px-2 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="`${row.platform}:${row.function_type}:${row.version}`" class="border-b border-[#eef2f5]">
                <td class="px-2 py-2 font-medium">{{ row.name }}</td>
                <td class="px-2 py-2">{{ mapPlatform(row.platform) }}</td>
                <td class="px-2 py-2">{{ mapFunctionType(row.function_type) }}</td>
                <td class="px-2 py-2">{{ row.version }}</td>
                <td class="px-2 py-2">{{ row.entry || "-" }}</td>
                <td class="px-2 py-2">{{ row.smoke_status || "-" }}</td>
                <td class="px-2 py-2">
                  <div class="flex items-center gap-2">
                    <button
                      v-if="canManageAlgo"
                      type="button"
                      :class="toggleSwitchClass(row.active)"
                      :disabled="togglingKey === buildRowKey(row)"
                      @click="toggleRowActive(row)"
                    >
                      <span :class="toggleThumbClass(row.active)" />
                    </button>
                    <span v-else class="scholar-pill">只读</span>
                    <span class="text-xs text-[#53626d]">{{ row.active ? "已启用" : "已停用" }}</span>
                  </div>
                </td>
                <td class="px-2 py-2">{{ formatTime(row.uploaded_at) }}</td>
                <td class="px-2 py-2">
                  <button
                    class="rounded border border-[#cbd5de] bg-white px-2 py-1 text-xs text-[#344250] disabled:cursor-not-allowed disabled:opacity-60"
                    :disabled="downloadingPackageKey === buildRowKey(row)"
                    @click="downloadRow(row)"
                  >
                    {{ downloadingPackageKey === buildRowKey(row) ? "下载中..." : "下载" }}
                  </button>
                </td>
              </tr>
              <tr v-if="rows.length === 0">
                <td colspan="9" class="px-2 py-4 text-center text-[#6b7782]">暂无算法包</td>
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
import { downloadAxiosBlobResponse } from "../../lib/download"
import { adminHttp } from "../../lib/http"
import { adminHasPermission } from "../../lib/session"

const rows = ref([])
const slots = ref([])
const strategyCards = ref([])
const selectedFile = ref(null)
const uploading = ref(false)
const togglingKey = ref("")
const savingStrategyKey = ref("")
const activateAfterUpload = ref(true)
const hintText = ref("")
const errorText = ref("")
const bootstrapping = ref(false)
const downloadingPackageKey = ref("")
const uploadForm = ref({
  platform: "cnki",
  function_type: "dedup",
})
const downloadingGuide = ref(false)

const canManageAlgo = computed(() => adminHasPermission("algo:manage"))

const platformOptions = [
  { value: "cnki", label: "知网" },
  { value: "vip", label: "维普" },
  { value: "paperpass", label: "PaperPass" },
]

const functionTypeOptions = [
  { value: "aigc_detect", label: "AIGC检测" },
  { value: "rewrite", label: "降AIGC率" },
  { value: "dedup", label: "降重复率" },
]

const platformOrder = {
  cnki: 1,
  vip: 2,
  paperpass: 3,
}

const taskTypeOrder = {
  aigc_detect: 1,
  rewrite: 2,
  dedup: 3,
}

onMounted(async () => {
  await Promise.all([loadPackages(), loadStrategies()])
})

async function loadPackages() {
  errorText.value = ""
  const data = await adminHttp.get("/admin/algo-packages")
  rows.value = data.items || []
  slots.value = data.slots || []
}

async function loadStrategies() {
  errorText.value = ""
  try {
    const data = await adminHttp.get("/admin/strategies")
    const items = Array.isArray(data.items) ? data.items : []
    strategyCards.value = items
      .map((item) => ({
        ...item,
        process_mode: item.process_mode === "algo_llm" ? "algo_llm" : "algo_only",
        is_enabled: Boolean(item.is_enabled),
        timeout_sec: Number(item.timeout_sec) > 0 ? Number(item.timeout_sec) : 300,
      }))
      .sort((a, b) => {
        const taskDiff = (taskTypeOrder[a.task_type] || 99) - (taskTypeOrder[b.task_type] || 99)
        if (taskDiff !== 0) {
          return taskDiff
        }
        return (platformOrder[a.platform] || 99) - (platformOrder[b.platform] || 99)
      })
  } catch (error) {
    errorText.value = error.message || "加载策略失败"
  }
}

async function saveStrategy(cell) {
  const key = `${cell.task_type}:${cell.platform}`
  savingStrategyKey.value = key
  hintText.value = ""
  errorText.value = ""
  try {
    const payload = {
      process_mode: cell.process_mode,
      is_enabled: Boolean(cell.is_enabled),
      timeout_sec: Number(cell.timeout_sec) || 300,
    }
    const saved = await adminHttp.put(`/admin/strategies/${cell.task_type}/${cell.platform}`, payload)
    Object.assign(cell, {
      process_mode: saved.process_mode,
      is_enabled: Boolean(saved.is_enabled),
      timeout_sec: Number(saved.timeout_sec) || 300,
      active_package: saved.active_package || cell.active_package || null,
      updated_at: saved.updated_at,
      updated_by: saved.updated_by,
    })
    hintText.value = `策略已保存：${mapStrategyPlatform(cell.platform)} / ${mapFunctionType(cell.task_type)}`
  } catch (error) {
    errorText.value = error.message || "保存策略失败"
  } finally {
    savingStrategyKey.value = ""
  }
}

function onFileChange(event) {
  const file = event?.target?.files?.[0] || null
  selectedFile.value = file
}

async function uploadPackage() {
  if (!selectedFile.value) {
    return
  }
  uploading.value = true
  hintText.value = ""
  errorText.value = ""
  try {
    const form = new FormData()
    form.append("platform", uploadForm.value.platform)
    form.append("function_type", uploadForm.value.function_type)
    form.append("activate", String(activateAfterUpload.value))
    form.append("file", selectedFile.value)
    const data = await adminHttp.post("/admin/algo-packages/upload", form)
    hintText.value = `上传成功：${mapPlatform(data.platform)}/${mapFunctionType(data.function_type)} @ ${data.version}`
    selectedFile.value = null
    await Promise.all([loadPackages(), loadStrategies()])
  } catch (error) {
    errorText.value = error.message || "上传失败"
  } finally {
    uploading.value = false
  }
}

async function downloadGuide() {
  downloadingGuide.value = true
  hintText.value = ""
  errorText.value = ""
  try {
    const response = await adminHttp.get("/admin/algo-packages/authoring-bundle", { responseType: "blob" })
    downloadAxiosBlobResponse(response, "ALGO_PACKAGE_AUTHORING_SPEC_BUNDLE.zip")
    hintText.value = "算法包编写规范包已开始下载。"
  } catch (error) {
    errorText.value = error.message || "下载算法包编写规范失败"
  } finally {
    downloadingGuide.value = false
  }
}

async function bootstrapBuiltinPackages() {
  bootstrapping.value = true
  hintText.value = ""
  errorText.value = ""
  try {
    const data = await adminHttp.post("/admin/algo-packages/bootstrap", {})
    hintText.value = `已完成初始化：${data.count || 0} 个算法包已写入并激活对应槽位。`
    await Promise.all([loadPackages(), loadStrategies()])
  } catch (error) {
    errorText.value = error.message || "初始化算法包失败"
  } finally {
    bootstrapping.value = false
  }
}

async function downloadRow(row) {
  const key = buildRowKey(row)
  downloadingPackageKey.value = key
  hintText.value = ""
  errorText.value = ""
  try {
    const response = await adminHttp.get("/admin/algo-packages/download", {
      params: {
        platform: row.platform,
        function_type: row.function_type,
        version: row.version,
      },
      responseType: "blob",
    })
    downloadAxiosBlobResponse(response, `algo_package_${row.platform}_${row.function_type}_${row.version}.zip`)
    hintText.value = `算法包已开始下载：${key}`
  } catch (error) {
    errorText.value = error.message || "下载算法包失败"
  } finally {
    downloadingPackageKey.value = ""
  }
}

async function toggleRowActive(row) {
  const key = buildRowKey(row)
  const enabling = !row.active
  const confirmText = enabling
    ? `确认启用 ${mapPlatform(row.platform)}/${mapFunctionType(row.function_type)} 到版本 ${row.version} 吗？`
    : `确认停用 ${mapPlatform(row.platform)}/${mapFunctionType(row.function_type)} 当前激活版本吗？`
  if (!window.confirm(confirmText)) {
    return
  }

  togglingKey.value = key
  hintText.value = ""
  errorText.value = ""
  try {
    if (enabling) {
      await adminHttp.post("/admin/algo-packages/activate", {
        platform: row.platform,
        function_type: row.function_type,
        version: row.version,
      })
      hintText.value = `已启用：${key}`
    } else {
      await adminHttp.post("/admin/algo-packages/deactivate", {
        platform: row.platform,
        function_type: row.function_type,
      })
      hintText.value = `已停用槽位：${mapPlatform(row.platform)}/${mapFunctionType(row.function_type)}`
    }
    await Promise.all([loadPackages(), loadStrategies()])
  } catch (error) {
    errorText.value = error.message || (enabling ? "启用失败" : "停用失败")
  } finally {
    togglingKey.value = ""
  }
}

function mapStrategyPlatform(platform) {
  return mapPlatform(platform)
}

function mapPlatform(platform) {
  const mapping = {
    cnki: "知网",
    vip: "维普",
    paperpass: "PaperPass",
  }
  return mapping[platform] || platform
}

function mapFunctionType(type) {
  const mapping = {
    aigc_detect: "AIGC检测",
    dedup: "降重复率",
    rewrite: "降AIGC率",
  }
  return mapping[type] || type
}

function buildRowKey(row) {
  return `${row.platform}:${row.function_type}:${row.version}`
}

function selectCardClass(current, value) {
  const active = current === value
  if (active) {
    return "rounded-xl border border-[#0f7a5f] bg-[#e8f4ef] px-3 py-3 text-left text-[#1d2b36]"
  }
  return "rounded-xl border border-[#cfd8e0] bg-white px-3 py-3 text-left text-[#3f4d58] hover:border-[#98adbb]"
}

function toggleSwitchClass(active) {
  return [
    "relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-60",
    active ? "bg-[#0f7a5f]" : "bg-[#cfd8e0]",
  ]
}

function toggleThumbClass(active) {
  return [
    "inline-block h-5 w-5 transform rounded-full bg-white transition-transform",
    active ? "translate-x-5" : "translate-x-1",
  ]
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}
</script>
