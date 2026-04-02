<template>
  <section class="overflow-hidden rounded-[28px] border border-[#d8dde3] bg-white shadow-[0_18px_45px_rgba(16,24,34,0.06)]">
    <div class="border-b border-[#e5eaef] bg-[linear-gradient(135deg,#f8f5ee,#eef4f8)] px-6 py-6">
      <div class="text-xs uppercase tracking-[0.18em] text-[#6d7781]">{{ sectionCode }}</div>
      <h2 class="mt-2 text-2xl font-semibold text-[#13202a]">{{ title }}</h2>
      <p class="mt-2 max-w-3xl text-sm leading-6 text-[#5c6872]">{{ hint }}</p>
    </div>

    <div class="space-y-5 px-6 py-6">
      <section class="rounded-3xl border border-[#dfe5eb] bg-[#f9fbfc] p-5">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-xs uppercase tracking-[0.14em] text-[#6b7b87]">Step 1</div>
            <div class="mt-1 text-base font-semibold text-[#1d2833]">选择目标平台</div>
          </div>
          <div class="text-xs text-[#6a7781]">默认推荐知网</div>
        </div>
        <div class="mt-4 grid gap-3 lg:grid-cols-3">
          <button
            v-for="item in platformOptions"
            :key="item.value"
            type="button"
            :class="platformCardClass(item.value)"
            @click="platform = item.value"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="text-sm font-semibold text-[#17222b]">{{ item.label }}</div>
                <div class="mt-1 text-xs leading-5 text-[#60707b]">{{ item.desc }}</div>
              </div>
              <span
                class="rounded-full px-2 py-1 text-[10px] tracking-[0.14em]"
                :class="platform === item.value ? 'bg-[#0f7a5f] text-white' : 'bg-[#edf2f6] text-[#5d6973]'"
              >
                {{ item.badge }}
              </span>
            </div>
          </button>
        </div>
      </section>

      <div :class="needReport ? 'grid gap-5 xl:grid-cols-2' : 'grid gap-5 xl:grid-cols-[1.2fr_0.8fr]'">
        <section class="rounded-3xl border border-[#dfe5eb] bg-[#f9fbfc] p-5">
          <div class="text-xs uppercase tracking-[0.14em] text-[#6b7b87]">Step 2</div>
          <div class="mt-1 text-base font-semibold text-[#1d2833]">上传主文件</div>
          <p class="mt-2 text-sm leading-6 text-[#5b6771]">{{ paperHint }}</p>

          <label class="mt-4 block cursor-pointer rounded-3xl border border-dashed border-[#b9c8d6] bg-white px-5 py-6 transition hover:border-[#8faea1] hover:bg-[#fbfdfd]">
            <input class="hidden" type="file" :accept="paperAcceptAttr" @change="onPaperChange" />
            <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div class="text-sm font-semibold text-[#1a2730]">点击上传文章</div>
                <div class="mt-1 text-xs text-[#687682]">支持格式：{{ formatExtList(paperAccept) }}</div>
              </div>
              <span class="rounded-full bg-[#eef3f7] px-3 py-1 text-xs text-[#55636f]">上限 20MB</span>
            </div>
          </label>

          <div v-if="paperFile" class="mt-4 rounded-2xl border border-[#d7e1e8] bg-white p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-semibold text-[#16212b]">{{ paperFile.name }}</div>
                <div class="mt-2 flex flex-wrap gap-2 text-xs text-[#61707b]">
                  <span class="rounded-full bg-[#eef3f7] px-2 py-1">{{ humanSize(paperFile.size) }}</span>
                  <span class="rounded-full bg-[#eef3f7] px-2 py-1">
                    {{ charCount > 0 ? `${charCount} 字符` : "字符数提交后以后端解析为准" }}
                  </span>
                </div>
              </div>
              <button class="rounded-full bg-[#eef3f7] px-3 py-1.5 text-xs text-[#32414f]" @click="clearPaper">
                删除
              </button>
            </div>
          </div>
        </section>

        <section v-if="needReport" class="rounded-3xl border border-[#dfe5eb] bg-[#f9fbfc] p-5">
          <div class="flex items-center justify-between gap-3">
            <div>
              <div class="text-xs uppercase tracking-[0.14em] text-[#6b7b87]">Step 3</div>
              <div class="mt-1 text-base font-semibold text-[#1d2833]">上传辅助报告</div>
            </div>
            <span class="rounded-full bg-[#edf2f6] px-3 py-1 text-xs text-[#5b6771]">可选</span>
          </div>
          <p class="mt-2 text-sm leading-6 text-[#5b6771]">{{ reportHint }}</p>
          <p v-if="reportHelp" class="mt-1 text-xs leading-5 text-[#6a7781]">{{ reportHelp }}</p>

          <label class="mt-4 block cursor-pointer rounded-3xl border border-dashed border-[#b9c8d6] bg-white px-5 py-6 transition hover:border-[#8faea1] hover:bg-[#fbfdfd]">
            <input class="hidden" type="file" :accept="reportAcceptAttr" @change="onReportChange" />
            <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div class="text-sm font-semibold text-[#1a2730]">{{ reportLabel }}</div>
                <div class="mt-1 text-xs text-[#687682]">支持格式：{{ formatExtList(reportAccept) }}</div>
              </div>
              <span class="rounded-full bg-[#eef3f7] px-3 py-1 text-xs text-[#55636f]">按报告结构自动校验</span>
            </div>
          </label>

          <div v-if="reportFile" class="mt-4 rounded-2xl border border-[#d7e1e8] bg-white p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-semibold text-[#16212b]">{{ reportFile.name }}</div>
                <div class="mt-2 flex flex-wrap gap-2 text-xs text-[#61707b]">
                  <span class="rounded-full bg-[#eef3f7] px-2 py-1">{{ humanSize(reportFile.size) }}</span>
                  <span class="rounded-full bg-[#eef3f7] px-2 py-1">提交后校验全文报告</span>
                </div>
              </div>
              <button class="rounded-full bg-[#eef3f7] px-3 py-1.5 text-xs text-[#32414f]" @click="clearReport">
                删除
              </button>
            </div>
          </div>
        </section>
      </div>

      <section class="rounded-3xl border border-[#dfe5eb] bg-[#f9fbfc] p-5">
        <div class="text-xs uppercase tracking-[0.14em] text-[#6b7b87]">Step {{ needReport ? 4 : 3 }}</div>
        <div class="mt-1 text-base font-semibold text-[#1d2833]">费用确认与提交</div>
        <div class="mt-4 space-y-3 rounded-2xl border border-[#dce4eb] bg-white p-4 text-sm text-[#485763]">
          <div class="flex items-center justify-between gap-3">
            <span>当前平台</span>
            <span class="font-medium text-[#18242d]">{{ platformLabel }}</span>
          </div>
          <div class="flex items-center justify-between gap-3">
            <span>预计字符数</span>
            <span class="font-medium text-[#18242d]">{{ charCount > 0 ? charCount : "提交后解析" }}</span>
          </div>
          <div class="flex items-center justify-between gap-3">
            <span>预计消耗积分</span>
            <span class="font-medium text-[#18242d]">{{ estimatedCostText }}</span>
          </div>
          <div class="flex items-center justify-between gap-3">
            <span>当前积分</span>
            <span class="font-medium text-[#18242d]">{{ displayCredits }}</span>
          </div>
          <div class="rounded-2xl bg-[#f5f8fa] px-3 py-3 text-xs leading-5 text-[#60707c]">
            {{ chargeExplainText }}
          </div>
          <div v-if="insufficient" class="rounded-2xl border border-[#f1d1c7] bg-[#fff4f1] px-3 py-3 text-sm text-[#a44431]">
            积分不足，请先充值后再提交任务。
          </div>
        </div>

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            class="rounded-2xl bg-[#0f7a5f] px-5 py-3 text-sm text-white shadow-[0_10px_22px_rgba(15,122,95,0.18)] disabled:cursor-not-allowed disabled:bg-[#87b7aa] disabled:shadow-none"
            :disabled="!canSubmit"
            @click="submit"
          >
            {{ submitting ? "提交中..." : actionText }}
          </button>
          <button class="rounded-2xl bg-[#edf2f6] px-4 py-3 text-sm text-[#344250]" @click="$emit('go-history')">
            查看任务记录
          </button>
        </div>
      </section>

      <p v-if="errorText" class="rounded-2xl border border-[#f2ccc4] bg-[#fff5f2] px-4 py-3 text-sm text-[#af3f33]">
        {{ errorText }}
      </p>
      <p v-if="successText" class="rounded-2xl border border-[#cfe6db] bg-[#eef8f2] px-4 py-3 text-sm text-[#106c4f]">
        {{ successText }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import { userHttp } from "../lib/http"
import { ensureUserLogin } from "../lib/requireLogin"

const props = defineProps({
  title: { type: String, required: true },
  hint: { type: String, required: true },
  actionText: { type: String, required: true },
  taskType: { type: String, required: true },
  costRate: { type: Number, required: true },
  needReport: { type: Boolean, default: false },
  reportLabel: { type: String, default: "可选报告文件" },
  reportHint: { type: String, default: "" },
  reportHelp: { type: String, default: "" },
  paperHint: { type: String, default: "" },
  paperAccept: { type: Array, default: () => [".docx", ".pdf", ".txt"] },
  reportAccept: { type: Array, default: () => [".docx", ".pdf"] },
  credits: { type: Number, default: null },
})

const emit = defineEmits(["submitted", "go-history"])
const router = useRouter()
const route = useRoute()

const platform = ref("cnki")
const paperFile = ref(null)
const reportFile = ref(null)
const charCount = ref(0)
const submitting = ref(false)
const errorText = ref("")
const successText = ref("")

const sectionCode = computed(() => {
  const mapping = {
    aigc_detect: "AIGC Detect",
    dedup: "Dedup Rewrite",
    rewrite: "AIGC Reduction",
  }
  return mapping[props.taskType] || "Task Submit"
})

const platformOptions = computed(() => {
  if (props.taskType === "dedup") {
    return [
      { value: "cnki", label: "知网 CNKI", desc: "偏重学位论文场景，适合做正式查重前的降重准备。", badge: "论文" },
      { value: "vip", label: "维普 VIP", desc: "更适合期刊稿件表达规整与句式调整。", badge: "期刊" },
      { value: "paperpass", label: "PaperPass", desc: "适合初筛和快速预审，强调效率与覆盖面。", badge: "预审" },
    ]
  }
  if (props.taskType === "rewrite") {
    return [
      { value: "cnki", label: "知网 CNKI", desc: "面向学术正文，控制表达痕迹并尽量保持论点稳定。", badge: "学术" },
      { value: "vip", label: "维普 VIP", desc: "适合投稿前的语言整理和段落表达调整。", badge: "投稿" },
      { value: "paperpass", label: "PaperPass", desc: "偏向快速降AIGC率处理和初次优化。", badge: "效率" },
    ]
  }
  return [
    { value: "cnki", label: "知网 CNKI", desc: "高校论文常用标准，适合正式提交前排查 AI 风险。", badge: "推荐" },
    { value: "vip", label: "维普 VIP", desc: "适合期刊稿件和研究类文本的表达波动检测。", badge: "期刊" },
    { value: "paperpass", label: "PaperPass", desc: "适合快速预检，及时发现高风险段落。", badge: "快速" },
  ]
})

const insufficient = computed(() => {
  if (props.credits == null || charCount.value <= 0) {
    return false
  }
  return props.credits < charCount.value * props.costRate
})

const canSubmit = computed(() => Boolean(paperFile.value) && !submitting.value && !insufficient.value)
const displayCredits = computed(() => {
  if (props.credits == null) {
    return "--"
  }
  return Number(props.credits).toLocaleString()
})
const platformLabel = computed(() => {
  const row = platformOptions.value.find((item) => item.value === platform.value)
  return row ? row.label : platform.value
})
const estimatedCostText = computed(() => {
  if (charCount.value <= 0) {
    return "提交后按后端解析结果计算"
  }
  return `${(charCount.value * props.costRate).toLocaleString()} 积分`
})
const chargeExplainText = computed(() => {
  if (props.taskType === "aigc_detect") {
    return "按正文字符计费，检测失败自动退积分。"
  }
  if (props.taskType === "dedup") {
    return "按论文正文字符计费；上传查重报告后，系统会优先按报告定位高重复内容。"
  }
  return "按论文正文字符计费；上传 AIGC 检测报告后，系统会优先处理高风险段落以降低AIGC率。"
})

const paperAcceptAttr = computed(() => props.paperAccept.join(","))
const reportAcceptAttr = computed(() => props.reportAccept.join(","))

function platformCardClass(value) {
  if (platform.value === value) {
    return "rounded-3xl border border-[#0f7a5f] bg-[linear-gradient(160deg,#edf7f3,#ffffff)] p-4 text-left shadow-[0_12px_24px_rgba(15,122,95,0.12)]"
  }
  return "rounded-3xl border border-[#d2dbe3] bg-white p-4 text-left transition hover:border-[#90afa3]"
}

function formatExtList(exts) {
  return exts.join(" / ")
}

function humanSize(size) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

function clearPaper() {
  paperFile.value = null
  charCount.value = 0
  errorText.value = ""
}

function clearReport() {
  reportFile.value = null
  errorText.value = ""
}

function fileExt(file) {
  return file?.name?.slice(file.name.lastIndexOf(".")).toLowerCase() || ""
}

function validateSelectedFile(file, allowedExts, emptyMessage) {
  if (!file) {
    return emptyMessage
  }
  const ext = fileExt(file)
  if (!allowedExts.includes(ext)) {
    return `仅支持 ${formatExtList(allowedExts)}`
  }
  if (file.size > 20 * 1024 * 1024) {
    return "文件超过20MB限制"
  }
  return ""
}

async function onPaperChange(event) {
  errorText.value = ""
  successText.value = ""
  const file = event.target.files?.[0]
  const err = validateSelectedFile(file, props.paperAccept, "未选择主文件")
  if (err) {
    clearPaper()
    errorText.value = err
    return
  }
  paperFile.value = file
  if (fileExt(file) === ".txt") {
    const text = await file.text()
    charCount.value = text.replace(/[\s\p{P}]/gu, "").length
  } else {
    charCount.value = 0
  }
}

function onReportChange(event) {
  errorText.value = ""
  successText.value = ""
  const file = event.target.files?.[0]
  if (!file) {
    clearReport()
    return
  }
  const err = validateSelectedFile(file, props.reportAccept, "未选择报告文件")
  if (err) {
    clearReport()
    errorText.value = err
    return
  }
  reportFile.value = file
}

async function submit() {
  if (!ensureUserLogin(router, route, route.fullPath || "/app/detect")) {
    return
  }
  if (!paperFile.value) {
    errorText.value = "请先上传主文件"
    return
  }
  submitting.value = true
  errorText.value = ""
  successText.value = ""
  try {
    const form = new FormData()
    form.append("task_type", props.taskType)
    form.append("platform", platform.value)
    form.append("paper", paperFile.value)
    if (reportFile.value) {
      form.append("report", reportFile.value)
    }
    const data = await userHttp.post("/tasks/submit", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    successText.value = `任务已提交，系统已生成任务 #${data.id}`
    emit("submitted", data)
  } catch (error) {
    errorText.value = error.message || "提交失败"
  } finally {
    submitting.value = false
  }
}
</script>
