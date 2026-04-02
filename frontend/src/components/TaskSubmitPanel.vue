<template>
  <section class="scholar-panel">
    <div class="scholar-panel__header">
      <div class="scholar-kicker">{{ sectionCode }}</div>
      <h2 class="scholar-title">{{ title }}</h2>
      <p class="scholar-lead">{{ hint }}</p>
    </div>

    <div class="scholar-panel__body">
      <div class="scholar-grid scholar-grid--form">
        <div class="scholar-stack">
          <section class="scholar-panel scholar-panel--soft">
            <div class="scholar-panel__body">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <div class="scholar-kicker">Step 1</div>
                  <h3 class="scholar-subtitle">选择目标平台</h3>
                </div>
                <span class="scholar-pill">默认推荐知网 CNKI</span>
              </div>

              <div class="scholar-option-grid lg:grid-cols-3" style="margin-top: 18px">
                <button
                  v-for="item in platformOptions"
                  :key="item.value"
                  type="button"
                  class="scholar-option-card"
                  :class="{ 'is-active': platform === item.value }"
                  @click="platform = item.value"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <div class="text-sm font-semibold text-[var(--ink)]">{{ item.label }}</div>
                      <div class="mt-2 text-xs leading-6 text-[var(--ink-soft)]">{{ item.desc }}</div>
                    </div>
                    <span
                      class="scholar-badge"
                      :class="platform === item.value ? 'scholar-badge--success' : 'scholar-badge--info'"
                    >
                      {{ item.badge }}
                    </span>
                  </div>
                </button>
              </div>
            </div>
          </section>

          <section class="scholar-panel scholar-panel--soft">
            <div class="scholar-panel__body">
              <div class="scholar-kicker">Step 2</div>
              <h3 class="scholar-subtitle">上传正文文件</h3>
              <p class="scholar-lead">{{ paperHint }}</p>

              <label class="scholar-dropzone" style="margin-top: 18px">
                <input class="hidden" type="file" :accept="paperAcceptAttr" @change="onPaperChange" />
                <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div class="text-sm font-semibold text-[var(--ink)]">点击上传论文正文</div>
                    <div class="mt-2 text-xs text-[var(--ink-soft)]">
                      支持格式：{{ formatExtList(paperAccept) }}
                    </div>
                  </div>
                  <span class="scholar-pill">单文件上限 20MB</span>
                </div>
              </label>

              <div v-if="paperFile" class="scholar-file-card" style="margin-top: 18px">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0 flex-1">
                    <div class="truncate text-sm font-semibold text-[var(--ink)]">{{ paperFile.name }}</div>
                    <div class="mt-3 flex flex-wrap gap-2">
                      <span class="scholar-pill">{{ humanSize(paperFile.size) }}</span>
                      <span class="scholar-pill">
                        {{ charCount > 0 ? `${charCount} 字符` : "字符数提交后以后端解析为准" }}
                      </span>
                    </div>
                  </div>
                  <button
                    class="scholar-button scholar-button--secondary"
                    type="button"
                    @click="clearPaper"
                  >
                    删除
                  </button>
                </div>
              </div>
            </div>
          </section>

          <section v-if="needReport" class="scholar-panel scholar-panel--soft">
            <div class="scholar-panel__body">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <div class="scholar-kicker">Step 3</div>
                  <h3 class="scholar-subtitle">上传辅助报告</h3>
                </div>
                <span class="scholar-pill">可选</span>
              </div>
              <p class="scholar-lead">{{ reportHint }}</p>
              <p v-if="reportHelp" class="scholar-muted text-sm leading-7">{{ reportHelp }}</p>

              <label class="scholar-dropzone" style="margin-top: 18px">
                <input class="hidden" type="file" :accept="reportAcceptAttr" @change="onReportChange" />
                <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div class="text-sm font-semibold text-[var(--ink)]">{{ reportLabel }}</div>
                    <div class="mt-2 text-xs text-[var(--ink-soft)]">
                      支持格式：{{ formatExtList(reportAccept) }}
                    </div>
                  </div>
                  <span class="scholar-pill">按报告结构自动校验</span>
                </div>
              </label>

              <div v-if="reportFile" class="scholar-file-card" style="margin-top: 18px">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0 flex-1">
                    <div class="truncate text-sm font-semibold text-[var(--ink)]">{{ reportFile.name }}</div>
                    <div class="mt-3 flex flex-wrap gap-2">
                      <span class="scholar-pill">{{ humanSize(reportFile.size) }}</span>
                      <span class="scholar-pill">提交后校验全量报告结构</span>
                    </div>
                  </div>
                  <button
                    class="scholar-button scholar-button--secondary"
                    type="button"
                    @click="clearReport"
                  >
                    删除
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>

        <div class="scholar-stack">
          <section class="scholar-panel scholar-panel--soft">
            <div class="scholar-panel__body">
              <div class="scholar-kicker">Step {{ needReport ? 4 : 3 }}</div>
              <h3 class="scholar-subtitle">提交前确认</h3>

              <div class="scholar-stack" style="margin-top: 18px">
                <div class="scholar-stat">
                  <div class="scholar-stat__label">目标平台</div>
                  <div class="scholar-stat__value" style="font-size: 26px">{{ platformLabel }}</div>
                </div>
                <div class="scholar-grid scholar-grid--halves">
                  <div class="scholar-stat">
                    <div class="scholar-stat__label">预计字符数</div>
                    <div class="scholar-stat__value" style="font-size: 24px">
                      {{ charCount > 0 ? charCount : "--" }}
                    </div>
                    <div class="scholar-stat__hint">Word/PDF 以后端解析为准</div>
                  </div>
                  <div class="scholar-stat">
                    <div class="scholar-stat__label">预计消耗</div>
                    <div class="scholar-stat__value" style="font-size: 24px">
                      {{ charCount > 0 ? `${(charCount * props.costRate).toLocaleString()} 分` : "--" }}
                    </div>
                    <div class="scholar-stat__hint">按字符数 × 单价计算</div>
                  </div>
                </div>

                <div class="scholar-note">
                  <div class="flex items-center justify-between gap-3">
                    <span>当前积分</span>
                    <strong>{{ displayCredits }}</strong>
                  </div>
                  <div style="margin-top: 10px">{{ chargeExplainText }}</div>
                </div>

                <div v-if="insufficient" class="scholar-note scholar-note--danger">
                  当前积分不足，请先充值后再提交任务。
                </div>

                <div class="scholar-inline-actions">
                  <button
                    class="scholar-button"
                    type="button"
                    :disabled="!canSubmit"
                    @click="submit"
                  >
                    {{ submitting ? "提交中..." : actionText }}
                  </button>
                  <button
                    class="scholar-button scholar-button--secondary"
                    type="button"
                    @click="$emit('go-history')"
                  >
                    查看任务记录
                  </button>
                </div>
              </div>
            </div>
          </section>

          <section class="scholar-panel scholar-panel--soft">
            <div class="scholar-panel__body">
              <div class="scholar-kicker">Writing Notes</div>
              <h3 class="scholar-subtitle">执行提示</h3>
              <div class="scholar-stack" style="margin-top: 16px">
                <div class="scholar-note">建议正文使用可编辑源文件，便于系统提取文本并保留结构。</div>
                <div class="scholar-note">上传辅助报告后，系统会优先处理命中的高风险段落或高重复段落。</div>
                <div class="scholar-note">处理完成后可在任务记录页查看摘要、下载结果和失败原因。</div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <p v-if="errorText" class="scholar-note scholar-note--danger" style="margin-top: 18px">
        {{ errorText }}
      </p>
      <p v-if="successText" class="scholar-note scholar-note--success" style="margin-top: 18px">
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
      { value: "cnki", label: "知网 CNKI", desc: "偏重学位论文场景，适合正式查重前的降重准备。", badge: "论文" },
      { value: "vip", label: "维普 VIP", desc: "更适合期刊稿件表达规整与句式调整。", badge: "期刊" },
      { value: "paperpass", label: "PaperPass", desc: "适合初筛和快速预审，强调效率与覆盖面。", badge: "预审" },
    ]
  }
  if (props.taskType === "rewrite") {
    return [
      { value: "cnki", label: "知网 CNKI", desc: "面向学术正文，控制表达痕迹并尽量保持论点稳定。", badge: "学术" },
      { value: "vip", label: "维普 VIP", desc: "适合投稿前的语言整理和段落表达调整。", badge: "投稿" },
      { value: "paperpass", label: "PaperPass", desc: "偏向快速降 AIGC 率处理和初次优化。", badge: "效率" },
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
const chargeExplainText = computed(() => {
  if (props.taskType === "aigc_detect") {
    return "按正文字符计费，检测失败自动退回积分。"
  }
  if (props.taskType === "dedup") {
    return "按论文正文字符计费；上传查重报告后，系统会优先按报告定位高重复内容。"
  }
  return "按论文正文字符计费；上传 AIGC 报告后，系统会优先处理高风险段落以降低 AIGC 率。"
})

const paperAcceptAttr = computed(() => props.paperAccept.join(","))
const reportAcceptAttr = computed(() => props.reportAccept.join(","))

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
    return "文件超过 20MB 限制"
  }
  return ""
}

async function onPaperChange(event) {
  errorText.value = ""
  successText.value = ""
  const file = event.target.files?.[0]
  const err = validateSelectedFile(file, props.paperAccept, "未选择正文文件")
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
    errorText.value = "请先上传正文文件"
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
