<template>
  <UserShell
    title="智能审稿"
    subtitle="对论文进行结构、论证、规范与语言表达预审，前端页面已开放，核心能力开发中。"
    :credits="userCredits"
    :hide-topbar="true"
    @buy="showBuy = !showBuy"
  >
    <section class="uploadPage_content">
      <div class="uploadLiterature_content">
        <div class="uploadLit_title">
          <span>上传智能审稿文档</span>
        </div>

        <div class="uploadLit_tips">
          <i>!</i>
          <span>智能审稿功能正在接入任务队列与报告详情，本页面用于确认交互流程与参数项。</span>
        </div>

        <div class="uploadLit_content">
          <div class="uploadLit_content_l">
            <div class="uploadLit_tabCon">
              <div class="uploadFormContent">
                <div class="uploadForm_con">
                  <section class="aigc-group">
                    <h3 class="aigc-group__title">
                      <span class="aigc-required">*</span>
                      选择检测平台
                      <span class="service-required-tag">必填</span>
                    </h3>
                    <div class="aigc-platform-grid">
                      <button
                        v-for="item in platformCards"
                        :key="item.value"
                        type="button"
                        class="aigc-platform-card"
                        :class="{ 'is-active': selectedPlatform === item.value }"
                        @click="selectedPlatform = item.value"
                      >
                        <div class="aigc-platform-card__name">{{ item.label }}</div>
                        <p class="aigc-platform-card__desc">{{ item.desc }}</p>
                      </button>
                    </div>
                  </section>

                  <section class="aigc-group">
                    <h3 class="aigc-group__title">
                      <span class="aigc-required">*</span>
                      待审稿件
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
                      <input class="hidden" type="file" accept=".docx,.pdf" @change="onPaperInput" />
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
                        <p class="aigc-upload__title">请将论文拖拽至此区域，或 <span>点击上传</span></p>
                        <p class="aigc-upload__subtitle">支持 .docx / .pdf，后续将接入审稿任务链路</p>
                      </div>
                    </label>
                    <p v-if="paperFile" class="aigc-upload__file">
                      {{ paperFile.name }}（{{ humanSize(paperFile.size) }}）
                      <button type="button" @click="clearPaper">移除</button>
                    </p>
                    <p v-if="fieldErrors.paper" class="aigc-field-error">{{ fieldErrors.paper }}</p>
                  </section>

                  <section class="aigc-group">
                    <h3 class="aigc-group__title">
                      审稿维度
                      <span class="service-optional-tag">可多选</span>
                    </h3>
                    <div class="aigc-type-grid">
                      <button
                        v-for="item in reviewDimensions"
                        :key="item.value"
                        type="button"
                        class="aigc-type-chip"
                        :class="{ 'is-active': selectedDimensions.includes(item.value) }"
                        @click="toggleDimension(item.value)"
                      >
                        {{ item.label }}
                      </button>
                    </div>
                  </section>

                  <section class="aigc-group">
                    <div class="aigc-field-row">
                      <label class="aigc-field-row__label">
                        额外说明
                        <span class="service-optional-tag">选填</span>
                      </label>
                      <div class="aigc-field-row__body">
                        <textarea
                          v-model="form.note"
                          class="aigc-input"
                          rows="4"
                          maxlength="300"
                          placeholder="例如：重点关注创新表达、引用格式、章节逻辑连贯性"
                        />
                        <div class="aigc-counter">{{ form.note.length }}/300</div>
                      </div>
                    </div>
                  </section>

                  <p class="service-warn-note">
                    智能审稿功能正在开发中，当前页面用于确认交互流程和视觉规范；提交入口暂未开放。
                  </p>

                  <div class="submitBtnCon">
                    <button class="scholar-button aigc-submit-action__button" type="button" disabled>正在开发中</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="uploadLit_content_r">
            <div class="uploadLit_content_right">
              <section class="aigc-side__law">
                审稿建议仅用于学术写作质量优化，不替代作者本人对学术规范与原创责任的最终把关。
                <a href="javascript:void(0)">详情&gt;&gt;</a>
                <a href="javascript:void(0)">相关报道&gt;&gt;</a>
              </section>
              <section class="aigc-side__hero">
                <img :src="reviewIllustration" alt="智能审稿流程图" />
              </section>
              <section class="aigc-side__brand">
                <div class="aigc-side__brand-icon">
                  <img :src="reviewMark" alt="" />
                </div>
                <h3>智能审稿服务</h3>
              </section>
              <p class="aigc-side__intro">将提供结构逻辑、表达规范、引用完整性与学术风险提示，帮助答辩前定向优化。</p>
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

import reviewMark from "../../assets/icons/review-mark.svg"
import reviewIllustration from "../../assets/illustrations/review-workbench.svg"
import BuyCreditsPanel from "../../components/BuyCreditsPanel.vue"
import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { getUserToken } from "../../lib/session"

const showBuy = ref(false)
const { user, refreshUser } = useUserProfile()
const userCredits = computed(() => {
  const value = user.value && user.value.credits
  return typeof value === "number" ? value : null
})

const selectedPlatform = ref("cnki")
const dragActive = ref(false)
const paperFile = ref(null)
const form = reactive({
  note: "",
})

const fieldErrors = reactive({
  paper: "",
})

const platformCards = [
  { value: "cnki", label: "格物学术标准审稿", desc: "偏重学位论文规范、章节逻辑与创新表达审阅。" },
  { value: "vip", label: "格物学术专业审稿", desc: "偏重期刊表达、摘要规范与关键词匹配质量审阅。" },
  { value: "paperpass", label: "格物学术极速审稿", desc: "偏重快速预审，突出高风险片段与结构问题定位。" },
]

const reviewDimensions = [
  { value: "logic", label: "论证逻辑" },
  { value: "citation", label: "引文规范" },
  { value: "language", label: "学术表达" },
  { value: "structure", label: "章节结构" },
  { value: "risk", label: "风险提示" },
]

const selectedDimensions = ref(["logic", "citation", "language"])

onMounted(async () => {
  if (getUserToken()) {
    await refreshUser()
  }
})

function toggleDimension(value) {
  if (selectedDimensions.value.includes(value)) {
    selectedDimensions.value = selectedDimensions.value.filter((item) => item !== value)
    return
  }
  selectedDimensions.value = [...selectedDimensions.value, value]
}

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
  if (!file) return

  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase()
  if (![".docx", ".pdf"].includes(ext)) {
    fieldErrors.paper = "仅支持 .docx / .pdf 文件"
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    fieldErrors.paper = "文件超过 20MB 限制"
    return
  }
  paperFile.value = file
}

async function afterPaid() {
  await refreshUser()
}
</script>
