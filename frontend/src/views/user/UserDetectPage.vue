<template>
  <UserShell
    title="AIGC检测"
    subtitle="按目标平台提交文档，系统会先校验积分，再生成检测记录并进入结果列表。"
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
                <span class="aigc-required">*</span> 上传正文文件
                <span class="service-required-tag">必填</span>
              </h3>
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
                  <p class="aigc-upload__title">请将待检测文档拖拽至区域 或 <span>点击上传</span></p>
                  <p class="aigc-upload__subtitle">当前支持识别中文、英文、中英文混合文本</p>
                </div>
              </label>
              <p class="aigc-upload__ext">支持扩展名：.docx / .pdf / .txt，单文件上限 20MB</p>
              <p v-if="paperFile" class="aigc-upload__file">
                {{ paperFile.name }}（{{ humanSize(paperFile.size) }}）
                <button type="button" @click="clearPaper">移除</button>
              </p>
              <p v-if="fieldErrors.paper" class="aigc-field-error">{{ fieldErrors.paper }}</p>
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
                    placeholder="请输入准确的文章篇名，信息将显示在检测报告单中"
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
                    placeholder="请输入作者姓名，多位作者请用分号分隔"
                  />
                  <div class="aigc-counter">{{ form.authors.length }}/200</div>
                </div>
              </div>
            </section>

            <div class="aigc-submit-action">
              <button class="scholar-button aigc-submit-action__button" type="button" :disabled="submitting" @click="submitTask">
                {{ submitting ? "提交中..." : "提交检测" }}
              </button>
            </div>
          </div>

          <aside class="aigc-side">
            <section class="aigc-side__law">
              根据学术规范要求，检测结果仅供作者自查与修改参考，禁止将服务用于替代原创写作。
              <a href="javascript:void(0)">详情&gt;&gt;</a>
              <a href="javascript:void(0)">相关报道&gt;&gt;</a>
            </section>

            <section class="aigc-side__brand">
              <div class="aigc-side__brand-icon">A</div>
              <h3>AIGC 检测服务</h3>
            </section>
            <p class="aigc-side__intro">
              右侧说明围绕风险识别、平台规则和结果归档展开，提交后可在记录页持续查看处理状态与下载入口。
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
                <li>支持仿知网、仿维普、仿PaperPass检测策略切换。</li>
                <li>报告保留 30 天，建议在个人中心及时下载归档。</li>
                <li>任务失败自动退回积分，不会产生额外扣费。</li>
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

const fieldErrors = reactive({
  paper: "",
  title: "",
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

const features = [
  {
    icon: "1",
    title: "结构化风险识别",
    desc: "输出整体风险占比、可疑段落位置与摘要提示，便于按章节逐段复核。",
  },
  {
    icon: "2",
    title: "多平台规则切换",
    desc: "同一流程覆盖仿知网、仿维普、仿PaperPass三类规则，减少重复提交。",
  },
  {
    icon: "3",
    title: "结果留档可追溯",
    desc: "每次提交自动写入任务记录，支持下载、复查与处理链路回溯。",
  },
  {
    icon: "4",
    title: "积分先校验再提交",
    desc: "提交前先完成计费校验，积分不足时即时提示，避免无效排队和等待。",
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
  if (route.query.platform && platformCards.find((item) => item.value === route.query.platform)) {
    form.platform = String(route.query.platform)
  }
})

function clearPaper() {
  paperFile.value = null
  fieldErrors.paper = ""
}

function humanSize(size) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

function onPaperInput(event) {
  const file = event.target.files?.[0] || null
  handlePaper(file)
  event.target.value = ""
}

function onDrop(event) {
  dragActive.value = false
  const file = event.dataTransfer?.files?.[0] || null
  handlePaper(file)
}

function handlePaper(file) {
  fieldErrors.paper = ""
  errorText.value = ""
  if (!file) return

  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase()
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
  let valid = true

  if (!paperFile.value) {
    fieldErrors.paper = "请先上传正文文件"
    valid = false
  }
  if (!form.title.trim()) {
    fieldErrors.title = "请填写篇名"
    valid = false
  }
  return valid
}

async function submitTask() {
  if (!ensureUserLogin(router, route, "/app/detect")) {
    return
  }
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
    if (form.authors.trim()) {
      payload.append("authors", form.authors.trim())
    }

    const data = await userHttp.post("/tasks/submit", payload, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    successText.value = `提交成功，任务 #${data.id} 已创建`
    await refreshUser()
    router.push({
      path: "/app/detect/records",
      query: { focus: String(data.id) },
    })
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
