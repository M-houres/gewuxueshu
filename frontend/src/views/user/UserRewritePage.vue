<template>
  <UserShell
    title="降AIGC率"
    subtitle="上传文档后提交任务，系统将按平台规则自动完成降AIGC处理并生成记录。"
    :credits="userCredits"
    :hide-topbar="true"
    :hide-header-title="true"
    @buy="showBuy = !showBuy"
  >
    <section class="uploadPage_content uploadPage_content--compact">
      <p v-if="errorText" class="aigc-alert aigc-alert--danger">{{ errorText }}</p>
      <p v-if="successText" class="aigc-alert aigc-alert--success">{{ successText }}</p>

      <section class="aigc-page-head">
        <h2 class="aigc-page-head__title">上传降 AIGC 处理文档</h2>
        <p class="aigc-page-head__notice">
          降AIGC率服务：在尽量保持原文语义和结构的前提下，对疑似AI特征段落进行优化处理。作为辅助处理工具服务，请结合导师要求与人工复核综合使用。
        </p>
      </section>

      <div class="uploadLiterature_content">
        <div class="uploadLit_content panels-container">
          <div class="uploadLit_content_l">
            <div class="uploadLit_tabCon">
              <div class="uploadFormContent">
                <div class="uploadForm_con">
                  <section class="aigc-group">
                    <h3 class="aigc-group__title"><span class="aigc-required">*</span>主文稿</h3>
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
                        <p class="aigc-upload__title">请上传待处理主文稿，或<span>点击上传</span></p>
                        <p class="aigc-upload__subtitle">主文稿仅支持 .docx</p>
                      </div>
                    </label>
                    <p class="aigc-upload__ext">单文件上限 20MB</p>
                    <p v-if="paperFile" class="aigc-upload__file">
                      {{ paperFile.name }}（{{ humanSize(paperFile.size) }}）
                      <button type="button" @click="clearPaper">移除</button>
                    </p>
                    <p v-if="fieldErrors.paper" class="aigc-field-error">{{ fieldErrors.paper }}</p>
                  </section>

                  <section class="aigc-group">
                    <div class="aigc-field-row aigc-field-row--platform">
                      <label class="aigc-field-row__label"><span class="aigc-required">*</span>平台选择</label>
                      <div class="aigc-field-row__body">
                        <div class="aigc-platform-grid aigc-platform-grid--inline">
                          <button
                            v-for="item in platformCards"
                            :key="item.value"
                            type="button"
                            class="aigc-platform-card"
                            :class="{ 'is-active': form.platform === item.value }"
                            @click="form.platform = item.value"
                          >
                            <div class="aigc-platform-card__name">{{ item.label }}</div>
                          </button>
                        </div>
                      </div>
                    </div>
                  </section>

                  <section class="aigc-group">
                    <div class="aigc-field-row">
                      <label class="aigc-field-row__label"><span class="aigc-required">*</span>篇名</label>
                      <div class="aigc-field-row__body">
                        <input
                          v-model="form.title"
                          class="aigc-input aigc-input--required"
                          :class="{ 'is-error': fieldErrors.title }"
                          type="text"
                          maxlength="300"
                          placeholder="请输入准确的文章篇名，信息将显示在处理报告中"
                        />
                        <div class="aigc-counter">{{ form.title.length }}/300</div>
                      </div>
                    </div>
                    <p v-if="fieldErrors.title" class="aigc-field-error">{{ fieldErrors.title }}</p>
                  </section>

                  <section class="aigc-group">
                    <div class="aigc-field-row">
                      <label class="aigc-field-row__label"><span class="aigc-required">*</span>作者</label>
                      <div class="aigc-field-row__body">
                        <input
                          v-model="form.authors"
                          class="aigc-input aigc-input--required"
                          :class="{ 'is-error': fieldErrors.authors }"
                          type="text"
                          maxlength="200"
                          placeholder='多位作者请使用 ";" 分隔'
                        />
                        <div class="aigc-counter">{{ form.authors.length }}/200</div>
                      </div>
                    </div>
                    <p v-if="fieldErrors.authors" class="aigc-field-error">{{ fieldErrors.authors }}</p>
                  </section>

                  <section class="aigc-group">
                    <h3 class="aigc-group__title">AIGC检测报告<span class="service-optional-tag">选填</span></h3>
                    <label
                      class="aigc-upload aigc-upload--green aigc-upload--compact"
                      :class="{ 'is-dragging': dragReport, 'is-error': fieldErrors.report }"
                      @dragenter.prevent="dragReport = true"
                      @dragover.prevent="dragReport = true"
                      @dragleave.prevent="dragReport = false"
                      @drop.prevent="onReportDrop"
                    >
                      <input class="hidden" type="file" accept=".docx,.pdf" @change="onReportInput" />
                      <div class="aigc-upload__inner">
                        <p class="aigc-upload__title">请上传 AIGC 检测全文报告（非截图/节选）</p>
                        <p class="aigc-upload__subtitle">全文报告支持 .docx / .pdf</p>
                      </div>
                    </label>
                    <p v-if="reportFile" class="aigc-upload__file">
                      {{ reportFile.name }}（{{ humanSize(reportFile.size) }}）
                      <button type="button" @click="clearReport">移除</button>
                    </p>
                    <p v-if="fieldErrors.report" class="aigc-field-error">{{ fieldErrors.report }}</p>
                  </section>

                  <div class="submitBtnCon">
                    <button class="aigc-submit-action__button" type="button" :disabled="submitting" @click="submitTask">
                      {{ submitting ? "提交中..." : "提交降AIGC" }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="uploadLit_content_r panel-right">
            <div class="uploadLit_content_right">
              <section class="aigc-side__law">
                对于代写、剽窃、伪造等学术不端行为，《中华人民共和国学位法》第三十七条进行了明确规定。
                <a href="javascript:void(0)">详情&gt;&gt;</a>
                <a href="javascript:void(0)">相关报道&gt;&gt;</a>
              </section>

              <section class="aigc-side__brand">
                <h3>降AIGC率服务</h3>
              </section>

              <section class="aigc-feature-list features-list">
                <article v-for="item in features" :key="item.title" class="aigc-feature-item">
                  <div class="aigc-feature-item__dot">{{ item.icon }}</div>
                  <div>
                    <h4>{{ item.title }}</h4>
                    <p>{{ item.desc }}</p>
                  </div>
                </article>
              </section>
            </div>
          </div>
        </div>
      </div>
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
  return typeof value === "number" ? value : null
})

const form = reactive({
  platform: "cnki",
  title: "",
  authors: "",
})

const platformCards = [
  { value: "cnki", label: "知网" },
  { value: "vip", label: "维普" },
  { value: "paperpass", label: "PaperPass" },
]

const features = [
  {
    icon: "1",
    title: "语义保持优化",
    desc: "围绕疑似AI特征段落进行结构重写与句式调整，在尽量保持核心观点和学术表达的基础上优化文本表现。",
  },
  {
    icon: "2",
    title: "平台规则适配",
    desc: "按所选平台执行处理策略，同一入口下完成一致化操作，减少重复调整成本。",
  },
  {
    icon: "3",
    title: "报告联动处理",
    desc: "支持上传AIGC检测报告作为辅助输入，优先处理高风险区域，提高修改效率与结果可用性。",
  },
  {
    icon: "4",
    title: "过程可追踪",
    desc: "每次提交均生成任务记录，可持续查看处理进度、回溯结果并下载文档，便于复核与交付。",
  },
]

const fieldErrors = reactive({
  paper: "",
  report: "",
  title: "",
  authors: "",
})

const dragMain = ref(false)
const dragReport = ref(false)
const paperFile = ref(null)
const reportFile = ref(null)
const submitting = ref(false)
const errorText = ref("")
const successText = ref("")

onMounted(async () => {
  const jobs = []
  if (getUserToken()) jobs.push(refreshUser())
  const platform = String(route.query.platform || "")
  if (platformCards.some((item) => item.value === platform)) {
    form.platform = platform
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
  if (!file) return

  const ext = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase() : ""
  if (ext !== ".docx") {
    fieldErrors.paper = "主文稿仅支持 .docx"
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
  if (!file) return

  const ext = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase() : ""
  if (![".docx", ".pdf"].includes(ext)) {
    fieldErrors.report = "AIGC 报告仅支持 .docx / .pdf"
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
  fieldErrors.authors = ""

  let valid = true
  if (!paperFile.value) {
    fieldErrors.paper = "请先上传主文稿"
    valid = false
  }
  if (!form.title.trim()) {
    fieldErrors.title = "请填写篇名"
    valid = false
  }
  if (!form.authors.trim()) {
    fieldErrors.authors = "请填写作者"
    valid = false
  }
  return valid
}

async function submitTask() {
  if (!ensureUserLogin(router, route, "/app/rewrite")) return

  if (!validateForm()) {
    errorText.value = "请先完成必填项后再提交"
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
    payload.append("authors", form.authors.trim())
    if (reportFile.value) payload.append("report", reportFile.value)

    const data = await userHttp.post("/tasks/submit", payload, {
      headers: { "Content-Type": "multipart/form-data" },
    })

    successText.value = `提交成功，任务 #${data.id} 已创建`
    await refreshUser()
    router.push({ path: "/app/rewrite/records", query: { focus: String(data.id) } })
  } catch (error) {
    errorText.value = error.message || "提交失败，请稍后重试"
  } finally {
    submitting.value = false
  }
}

async function afterPaid() {
  await refreshUser()
}
</script>
