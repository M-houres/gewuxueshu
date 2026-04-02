<template>
  <AdminShell title="算法包管理" subtitle="上传、激活与版本状态">
    <div class="space-y-4">
      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h3 class="text-base font-semibold">上传算法包</h3>
          <div class="flex flex-wrap items-center gap-2">
            <button
              class="rounded-lg border border-[#0f7a5f] bg-[#e8f4ef] px-3 py-2 text-sm text-[#0f6c53] hover:border-[#0d5f49] disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="bootstrapping"
              @click="bootstrapBuiltinPackages"
            >
              {{ bootstrapping ? "初始化中..." : "一键初始化知网+维普+PaperPass 算法包" }}
            </button>
            <button
              class="rounded-lg border border-[#cbd5de] bg-white px-3 py-2 text-sm text-[#344250] hover:border-[#8ca2b2] disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="downloadingGuide"
              @click="downloadGuide"
            >
              {{ downloadingGuide ? "下载中..." : "下载算法写作总规范包" }}
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
                <div class="mt-1 text-xs text-[#60707b]">{{ item.desc }}</div>
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
                <div class="mt-1 text-xs text-[#60707b]">{{ item.desc }}</div>
              </button>
            </div>
          </div>
          <div class="rounded-xl bg-[#eef4f9] px-3 py-2 text-xs text-[#4c5d69]">
            当前选择：{{ mapPlatform(uploadForm.platform) }} / {{ mapFunctionType(uploadForm.function_type) }}
          </div>
          <div class="rounded-xl border border-[#d8e4ee] bg-white px-3 py-3 text-xs leading-6 text-[#4c5d69]">
            <div class="font-semibold text-[#31414d]">上传前硬性要求</div>
            <div>1. 必须是 `zip`，且至少包含 `manifest.json` 与入口 Python 文件。</div>
            <div>2. `manifest.name` 只能用字母、数字、下划线、短横线；`version` 必须是语义化版本号。</div>
            <div>3. `platform`、`function_type` 必须和当前槽位完全一致，入口路径不能是绝对路径，也不能含 `..`。</div>
            <div>4. Python 文件和 `manifest.json` 必须是 UTF-8；`process` 必须可调用，且返回值不能是 `None`。</div>
            <div>5. 运行时会优先传入字符串文本；如果你的 `process` 只接收对象，也要兼容 `{"text": "..."}`。</div>
            <div>6. 当前默认单次执行超时 8 秒，上传包大小上限 200 MB。</div>
          </div>
        </div>
        <div class="mt-3 grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-center">
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
        <p v-if="hintText" class="mt-3 text-sm text-[#106c4f]">{{ hintText }}</p>
        <p v-if="errorText" class="mt-3 text-sm text-[#af3f33]">{{ errorText }}</p>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold">槽位当前版本</h3>
        <div class="mt-3 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">平台</th>
                <th class="px-2 py-2">功能类型</th>
                <th class="px-2 py-2">当前包名</th>
                <th class="px-2 py-2">当前版本</th>
                <th class="px-2 py-2">smoke</th>
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
          <h3 class="text-base font-semibold">已上传算法包</h3>
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
                <th class="px-2 py-2">smoke</th>
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
                    type="button"
                    :class="toggleSwitchClass(row.active)"
                    :disabled="togglingKey === buildRowKey(row)"
                    @click="toggleRowActive(row)"
                  >
                    <span :class="toggleThumbClass(row.active)" />
                  </button>
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
import { onMounted, ref } from "vue"

import AdminShell from "../../components/AdminShell.vue"
import { downloadAxiosBlobResponse } from "../../lib/download"
import { adminHttp } from "../../lib/http"

const rows = ref([])
const slots = ref([])
const selectedFile = ref(null)
const uploading = ref(false)
const togglingKey = ref("")
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
const platformOptions = [
  { value: "cnki", label: "知网 CNKI", desc: "高校论文检测规则" },
  { value: "vip", label: "维普 VIP", desc: "期刊库检测规则" },
  { value: "paperpass", label: "PaperPass", desc: "通用预审规则" },
]
const functionTypeOptions = [
  { value: "aigc_detect", label: "AIGC 检测", desc: "判断生成内容风险" },
  { value: "dedup", label: "降重复率", desc: "文本相似度处理" },
  { value: "rewrite", label: "降AIGC率", desc: "同文降AIGC改写优化" },
]

onMounted(loadPackages)

async function loadPackages() {
  errorText.value = ""
  const data = await adminHttp.get("/admin/algo-packages")
  rows.value = data.items || []
  slots.value = data.slots || []
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
    hintText.value = `上传成功：${data.platform}/${data.function_type} @ ${data.version}`
    selectedFile.value = null
    await loadPackages()
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
    hintText.value = "算法写作总规范包已开始下载。"
  } catch (error) {
    errorText.value = error.message || "下载算法写作总规范包失败"
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
    await loadPackages()
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
    ? `确认启用 ${row.platform}/${row.function_type} 槽位到版本 ${row.version} 吗？`
    : `确认停用 ${row.platform}/${row.function_type} 槽位当前激活版本吗？`
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
      hintText.value = `已停用槽位：${row.platform}/${row.function_type}`
    }
    await loadPackages()
  } catch (error) {
    errorText.value = error.message || (enabling ? "启用失败" : "停用失败")
  } finally {
    togglingKey.value = ""
  }
}

function mapPlatform(platform) {
  const mapping = {
    cnki: "知网 CNKI",
    vip: "维普 VIP",
    paperpass: "PaperPass",
  }
  return mapping[platform] || platform
}

function mapFunctionType(type) {
  const mapping = {
    aigc_detect: "AIGC 检测",
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
