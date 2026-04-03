<template>
  <UserShell
    title="降AIGC率"
    subtitle="上传正文与可选AIGC报告，系统按风险段落优先处理并生成新任务记录。"
    :credits="userCredits"
    :hide-topbar="true"
    @buy="showBuy = !showBuy"
  >
    <section class="aigc-submit-zone">
      <p v-if="errorText" class="aigc-alert aigc-alert--danger">{{ errorText }}</p>
      <p v-if="successText" class="aigc-alert aigc-alert--success">{{ successText }}</p>

      <article class="aigc-sheet">
        <div class="aigc-sheet__grid">
          <div class="aigc-form">
            <section class="aigc-group">
              <h3 class="aigc-group__title">
                <span class="aigc-required">*</span> 选择仿平台
                <span class="service-required-tag">必填</span>
              </h3>
              <div class="aigc-platform-grid">
                <button
                  v-for="item in platformCards"
                  :key="item.value"
                  type="button"
                  class="aigc-platform-card"
                  :class="{ 'is-active': form.platform === item.value }"
                  @click="form.platform = item.value"
                >
                  <div class="aigc-platform-card__name">{{ item.label }}</div>
                  <p class="aigc-platform-card__desc">{{ item.desc }}</p>
                </button>
              </div>
            </section>

            <section class="aigc-group">
              <h3 class="aigc-group__title">
                <span class="aigc-required">*</span> 主文档上传
                <span class="service-required-tag">必填</span>
              </h3>
              <label
                class="aigc-upload"
                :class="{ 'is-dragging': dragMain, 'is-error': fieldErrors.paper }"
                @dragenter.prevent="dragMain = true"
                @dragover.prevent="dragMain = true"
                @dragleave.prevent="dragMain = false"
                @drop.prevent="onMainDrop"
              >
                <input class="hidden" type="file" accept=".docx" @change="onPaperInput" />
                <div class="aigc-upload__inner">
                  <div class="aigc-upload__icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24">
                      <path
                        d="M6 2h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm7 1.5V7h3.5L13 3.5ZM8.5 12.5h7M8.5 16h7"
                        fill="none"
                        stroke="currentColor"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="1.6"
                      />
                    </svg>
                  </div>
                  <p class="aigc-upload__title">请将待处理文档拖拽至区域 或 <span>点击上传</span></p>
                  <p class="aigc-upload__subtitle">支持中文、英文与中英文混合文本</p>
                </div>
              </label>
              <p class="aigc-upload__ext">支持格式：.docx（单文件上限 20MB）</p>
              <p v-if="paperFile" class="aigc-upload__file">
                {{ paperFile.name }}（{{ humanSize(paperFile.size) }}）
                <button type="button" @click="clearPaper">移除</button>
              </p>
              <p v-if="fieldErrors.paper" class="aigc-field-error">{{ fieldErrors.paper }}</p>
            </section>

            <section class="aigc-group">
              <h3 class="aigc-group__title">
                AIGC报告上传
                <span class="service-optional-tag">选填</span>
              </h3>
              <label
                class="aigc-upload aigc-upload--green"
                :class="{ 'is-dragging': dragReport, 'is-error': fieldErrors.report }"
                @dragenter.prevent="dragReport = true"
                @dragover.prevent="dragReport = true"
                @dragleave.prevent="dragReport = false"
                @drop.prevent="onReportDrop"
              >
                <input class="hidden" type="file" accept=".docx,.pdf" @change="onReportInput" />
                <div class="aigc-upload__inner">
                  <div class="aigc-upload__icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24">
                      <path
                        d="M6 2h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm2.5 12 2 2 5-5"
                        fill="none"
                        stroke="currentColor"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="1.7"
                      />
                    </svg>
                  </div>
                  <p class="aigc-upload__title">可上传AIGC检测报告，系统会优先处理高风险段落</p>
                  <p class="aigc-upload__subtitle">上传后可提高降AIGC率处理命中度</p>
                </div>
              </label>
              <p class="aigc-upload__ext">支持格式：.docx / .pdf，不上传也可直接提交</p>
              <p v-if="reportFile" class="aigc-upload__file">
                {{ reportFile.name }}（{{ humanSize(reportFile.size) }}）
                <button type="button" @click="clearReport">移除</button>
              </p>
              <p v-if="fieldErrors.report" class="aigc-field-error">{{ fieldErrors.report }}</p>
            </section>

            <section class="aigc-group">
              <div class="aigc-field-row">
                <label class="aigc-field-row__label">
                  <span class="aigc-required">*</span> 篇名
                  <span class="service-required-tag">必填</span>
                </label>
                <div class="aigc-field-row__body">
                  <input
                    v-model="form.title"
                    class="aigc-input aigc-input--required"
                    :class="{ 'is-error': fieldErrors.title }"
                    type="text"
                    maxlength="300"
                    placeholder="请输入准确篇名，用于结果报告展示"
                  />
                  <div class="aigc-counter">{{ form.title.length }}/300</div>
                </div>
              </div>
              <p v-if="fieldErrors.title" class="aigc-field-error">{{ fieldErrors.title }}</p>
            </section>

            <section class="aigc-group">
              <div class="aigc-field-row">
                <label class="aigc-field-row__label">
                  作者
                  <span class="service-optional-tag">选填</span>
                </label>
                <div class="aigc-field-row__body">
                  <input
                    v-model="form.authors"
                    class="aigc-input"
                    type="text"
                    maxlength="200"
                    placeholder="多位作者请用分号分隔"
                  />
                  <div class="aigc-counter">{{ form.authors.length }}/200</div>
                </div>
              </div>
            </section>

            <div class="aigc-submit-action">
              <button class="scholar-button aigc-submit-action__button" type="button" :disabled="submitting" @click="submitTask">
                {{ submitting ? "提交中..." : "提交降AIGC率" }}
              </button>
            </div>
          </div>

          <aside class="aigc-side">
            <section class="aigc-side__law">
              根据学术规范要求，处理结果仅用于作者修改优化参考，不可替代原创写作与学术规范责任。
              <a href="javascript:void(0)">详情&gt;&gt;</a>
              <a href="javascript:void(0)">相关报道&gt;&gt;</a>
            </section>
            <section class="aigc-side__brand">
              <div class="aigc-side__brand-icon">R</div>
              <h3>降 AIGC 率服务</h3>
            </section>
            <p class="aigc-side__intro">
              在尽量保留原文论点和结构的前提下优化表达方式，重点处理高风险语句，降低文本中的 AI 痕迹感。
            </p>
            <section class="aigc-feature-list">
              <article v-for="item in features" :key="item.title" class="aigc-feature-item">
                <div class="aigc-feature-item__dot">{{ item.icon }}</div>
                <div>
                  <h4>{{ item.title }}</h4>
                  <p>{{ item.desc }}</p>
                </div>
              </article>
            </section>
            <section class="aigc-side__note">
              <div class="aigc-side__note-title">使用提醒</div>
              <ul>
                <li>主文档必填，AIGC报告选填；上传后可提高处理命中度。</li>
                <li>建议提交前确认篇名，便于结果列表检索与后续归档管理。</li>
                <li>任务创建后可在记录页查看进度、详情和下载入口。</li>
              </ul>
            </section>
          </aside>
        </div>
      </article>
    </section>

    <BuyCreditsPanel v-if="showBuy" @paid="afterPaid" />
  </UserShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import BuyCreditsPanel from "../../components/BuyCreditsPanel.vue"
import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { userHttp } from "../../lib/http"
import { ensureUserLogin } from "../../lib/requireLogin"
import { getUserToken } from "../../lib/session"

const router = useRouter()
const route = useRoute()
const showBuy = ref(false)
const { user, refreshUser } = useUserProfile()
const userCredits = computed(() => {
  const value = user.value && user.value.credits
  if (typeof value === "number") {
    return value
  }
  return null
})

const form = reactive({
  platform: "cnki",
  title: "",
  authors: "",
})

const platformCards = [
  {
    value: "cnki",
    label: "仿知网检测",
    desc: "适合学位论文与答辩前复核场景。",
  },
  {
    value: "vip",
    label: "仿维普检测",
    desc: "适合期刊稿件与项目文本预检。",
  },
  {
    value: "paperpass",
    label: "仿PaperPass检测",
    desc: "适合快速初筛与高风险段定位。",
  },
]

const fieldErrors = reactive({
  paper: "",
  report: "",
  title: "",
})

const features = [
  {
    icon: "1",
    title: "语义保留式改写",
    desc: "在尽量保留论点逻辑前提下重构句式，降低模板化表达带来的 AI 痕迹。",
  },
  {
    icon: "2",
    title: "高风险段落优先",
    desc: "结合报告命中信息优先处理高风险内容，先解决关键段落再优化整体表达。",
  },
  {
    icon: "3",
    title: "积分消费可追踪",
    desc: "按字符计费并实时校验余额，积分流水与任务记录同步沉淀，便于复核追踪。",
  },
  {
    icon: "4",
    title: "处理链路安全隔离",
    desc: "文件处理全程隔离，任务完成后可下载结果并在个人中心留档复核。",
  },
]

const dragMain = ref(false)
const dragReport = ref(false)
const paperFile = ref(null)
const reportFile = ref(null)
const submitting = ref(false)
const errorText = ref("")
const successText = ref("")

onMounted(async () => {
  const jobs = []
  if (getUserToken()) {
    jobs.push(refreshUser())
  }
  if (route.query.platform && platformCards.find((item) => item.value === route.query.platform)) {
    form.platform = String(route.query.platform)
  }
  await Promise.all(jobs)
})

function humanSize(size) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

function clearPaper() {
  paperFile.value = null
  fieldErrors.paper = ""
}

function clearReport() {
  reportFile.value = null
  fieldErrors.report = ""
}

function onPaperInput(event) {
  const file = event.target.files?.[0] || null
  setMainFile(file)
  event.target.value = ""
}

function onMainDrop(event) {
  dragMain.value = false
  const file = event.dataTransfer?.files?.[0] || null
  setMainFile(file)
}

function setMainFile(file) {
  fieldErrors.paper = ""
  if (!file) {
    return
  }
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase()
  if (ext !== ".docx") {
    fieldErrors.paper = "主文档仅支持 .docx"
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    fieldErrors.paper = "文件超过 20MB 限制"
    return
  }
  paperFile.value = file
}

function onReportInput(event) {
  const file = event.target.files?.[0] || null
  setReportFile(file)
  event.target.value = ""
}

function onReportDrop(event) {
  dragReport.value = false
  const file = event.dataTransfer?.files?.[0] || null
  setReportFile(file)
}

function setReportFile(file) {
  fieldErrors.report = ""
  if (!file) {
    return
  }
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase()
  if (![".docx", ".pdf"].includes(ext)) {
    fieldErrors.report = "AIGC报告仅支持 .docx / .pdf"
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    fieldErrors.report = "文件超过 20MB 限制"
    return
  }
  reportFile.value = file
}

function validateForm() {
  fieldErrors.paper = ""
  fieldErrors.title = ""
  let valid = true
  if (!paperFile.value) {
    fieldErrors.paper = "请先上传主文档"
    valid = false
  }
  if (!form.title.trim()) {
    fieldErrors.title = "请填写篇名"
    valid = false
  }
  return valid
}

async function submitTask() {
  if (!ensureUserLogin(router, route, "/app/rewrite")) {
    return
  }
  if (!validateForm()) {
    errorText.value = "请先完成必填项"
    return
  }

  submitting.value = true
  errorText.value = ""
  successText.value = ""
  try {
    const payload = new FormData()
    payload.append("task_type", "rewrite")
    payload.append("platform", form.platform)
    payload.append("paper", paperFile.value)
    payload.append("paper_title", form.title.trim())
    if (form.authors.trim()) {
      payload.append("authors", form.authors.trim())
    }
    if (reportFile.value) {
      payload.append("report", reportFile.value)
    }
    const data = await userHttp.post("/tasks/submit", payload, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    successText.value = `提交成功，任务 #${data.id} 已创建`
    await refreshUser()
    router.push({ path: "/app/rewrite/records", query: { focus: String(data.id) } })
  } catch (error) {
    errorText.value = error.message || "提交失败"
  } finally {
    submitting.value = false
  }
}

async function afterPaid() {
  await refreshUser()
}
</script>
