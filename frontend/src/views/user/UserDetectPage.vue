<template>
  <UserShell
    title="AIGC检测"
    subtitle="上传文档后提交检测，系统将根据平台规则自动处理并生成报告记录。"
    :credits="userCredits"
    :hide-topbar="true"
    :hide-header-title="true"
    @buy="showBuy = !showBuy"
  >
    <section class="uploadPage_content">
      <p v-if="errorText" class="aigc-alert aigc-alert--danger">{{ errorText }}</p>
      <p v-if="successText" class="aigc-alert aigc-alert--success">{{ successText }}</p>

      <section class="aigc-page-head">
        <h2 class="aigc-page-head__title">上传 AIGC 待检测文档</h2>
        <p class="aigc-page-head__notice">
          AIGC检测服务：可有效识别文本是否部分或全部具有AI模型生成特征。作为辅助检测工具服务，请结合实际情况综合研判使用。当前支持识别中文、英文、中英文混合文本。
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
                      :class="{ 'is-dragging': dragActive, 'is-error': fieldErrors.paper }"
                      @dragenter.prevent="dragActive = true"
                      @dragover.prevent="dragActive = true"
                      @dragleave.prevent="dragActive = false"
                      @drop.prevent="onDrop"
                    >
                      <input class="hidden" type="file" accept=".docx,.pdf,.txt" @change="onPaperInput" />
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
                        <p class="aigc-upload__title">请将待检测文档拖拽至区域，或<span>点击上传</span></p>
                        <p class="aigc-upload__subtitle">当前支持识别中文、英文、中英文混合文本</p>
                      </div>
                    </label>
                    <p class="aigc-upload__ext">支持 .docx / .pdf / .txt，单文件上限 20MB</p>
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
                          placeholder="请输入准确的文章篇名，信息将显示在检测报告单中"
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
                          placeholder='请填写作者信息，多位作者用 ";" 分隔'
                        />
                        <div class="aigc-counter">{{ form.authors.length }}/200</div>
                      </div>
                    </div>
                    <p v-if="fieldErrors.authors" class="aigc-field-error">{{ fieldErrors.authors }}</p>
                  </section>

                  <div class="submitBtnCon">
                    <button class="aigc-submit-action__button" type="button" :disabled="submitting" @click="submitTask">
                      {{ submitting ? "提交中..." : "提交检测" }}
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
                <a href="https://www.news.cn/legal/20240426/8fc9b903147a477a9dab550518d4ff80/c.html" target="_blank" rel="noopener noreferrer">详情&gt;&gt;</a>
                <a href="https://news.cctv.com/2024/04/26/ARTIxCmi4wUMPigs46qnoMeJ240426.shtml" target="_blank" rel="noopener noreferrer">相关报道&gt;&gt;</a>
              </section>

              <section class="aigc-side__brand">
                <h3>AIGC检测服务</h3>
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

const fieldErrors = reactive({
  paper: "",
  title: "",
  authors: "",
})

const platformCards = [
  { value: "cnki", label: "仿知网" },
  { value: "vip", label: "仿维普" },
  { value: "paperpass", label: "仿PaperPass" },
]

const features = [
  {
    icon: "1",
    title: "先进的检测技术",
    desc: "使用最先进的自然语言处理(NLP)技术，包括深度学习和人工智能，有效识别文本是否部分或全部具有AI模型生成特征。算法模型经过大量训练，具备高效检测能力。",
  },
  {
    icon: "2",
    title: "多格式类型检测",
    desc: "支持期刊投稿、学位论文、会议论文以及图书专著、科研成果、课程作业等检测。",
  },
  {
    icon: "3",
    title: "多层次报告展示",
    desc: "提供详细可视化检测报告，通过高亮和AI特征值标注，直观展示文本内容中的AI特征。",
  },
  {
    icon: "4",
    title: "可靠的安全保障",
    desc: "尊重并保护用户隐私和数据安全，采用加密技术，确保论文在上传和检测过程中不会被泄露。",
  },
]

const submitting = ref(false)
const dragActive = ref(false)
const paperFile = ref(null)
const errorText = ref("")
const successText = ref("")

onMounted(async () => {
  if (getUserToken()) {
    await refreshUser()
  }
  const platform = String(route.query.platform || "")
  if (platformCards.some((item) => item.value === platform)) {
    form.platform = platform
  }
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

function onPaperInput(event) {
  const file = event.target.files?.[0] || null
  setPaperFile(file)
  event.target.value = ""
}

function onDrop(event) {
  dragActive.value = false
  const file = event.dataTransfer?.files?.[0] || null
  setPaperFile(file)
}

function setPaperFile(file) {
  fieldErrors.paper = ""
  errorText.value = ""
  if (!file) return

  const ext = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase() : ""
  if (![".docx", ".pdf", ".txt"].includes(ext)) {
    fieldErrors.paper = "仅支持 .docx / .pdf / .txt 文件"
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    fieldErrors.paper = "文件超过 20MB 限制"
    return
  }
  paperFile.value = file
}

function validateForm() {
  fieldErrors.paper = ""
  fieldErrors.title = ""
  fieldErrors.authors = ""

  let valid = true
  if (!paperFile.value) {
    fieldErrors.paper = "请先上传检测文档"
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
  if (!ensureUserLogin(router, route, "/app/detect")) return

  if (!validateForm()) {
    errorText.value = "请先完成必填项后再提交"
    return
  }

  submitting.value = true
  errorText.value = ""
  successText.value = ""

  try {
    const payload = new FormData()
    payload.append("task_type", "aigc_detect")
    payload.append("platform", form.platform)
    payload.append("paper", paperFile.value)
    payload.append("paper_title", form.title.trim())
    payload.append("authors", form.authors.trim())

    const data = await userHttp.post("/tasks/submit", payload, {
      headers: { "Content-Type": "multipart/form-data" },
    })

    successText.value = `提交成功，任务 #${data.id} 已创建`
    await refreshUser()
    router.push({ path: "/app/detect/records", query: { focus: String(data.id) } })
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

