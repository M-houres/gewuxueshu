<template>
  <UserShell
    title="答辩服务"
    subtitle="覆盖开题、中期、预答辩与正式答辩准备流程，页面先行开放，功能开发中。"
    :credits="userCredits"
    :hide-topbar="true"
    @buy="showBuy = !showBuy"
  >
    <section class="uploadPage_content">
      <div class="uploadLiterature_content">
        <div class="uploadLit_title">
          <span>上传答辩服务文档</span>
        </div>

        <div class="uploadLit_tips">
          <i>!</i>
          <span>答辩服务功能正在接入任务队列与演练报告，本页面用于确认交互流程与参数项。</span>
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
                      答辩阶段
                      <span class="service-required-tag">必填</span>
                    </h3>
                    <div class="aigc-type-grid">
                      <button
                        v-for="item in defenseStages"
                        :key="item.value"
                        type="button"
                        class="aigc-type-chip"
                        :class="{ 'is-active': selectedStage === item.value }"
                        @click="selectedStage = item.value"
                      >
                        {{ item.label }}
                      </button>
                    </div>
                  </section>

                  <section class="aigc-group">
                    <h3 class="aigc-group__title">
                      <span class="aigc-required">*</span>
                      答辩材料
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
                      <input class="hidden" type="file" accept=".docx,.pdf,.ppt,.pptx" @change="onPaperInput" />
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
                        <p class="aigc-upload__title">上传论文正文、答辩PPT或摘要稿</p>
                        <p class="aigc-upload__subtitle">支持 .docx / .pdf / .ppt / .pptx</p>
                      </div>
                    </label>
                    <p v-if="paperFile" class="aigc-upload__file">
                      {{ paperFile.name }}（{{ humanSize(paperFile.size) }}）
                      <button type="button" @click="clearPaper">移除</button>
                    </p>
                    <p v-if="fieldErrors.paper" class="aigc-field-error">{{ fieldErrors.paper }}</p>
                  </section>

                  <section class="aigc-group">
                    <div class="aigc-field-row">
                      <label class="aigc-field-row__label">
                        重点关注
                        <span class="service-optional-tag">选填</span>
                      </label>
                      <div class="aigc-field-row__body">
                        <textarea
                          v-model="form.focus"
                          class="aigc-input"
                          rows="4"
                          maxlength="300"
                          placeholder="例如：创新点表达、方法合理性追问、局限性回答模板"
                        />
                        <div class="aigc-counter">{{ form.focus.length }}/300</div>
                      </div>
                    </div>
                  </section>

                  <p class="service-warn-note">
                    答辩服务正在开发中，当前页面用于展示提交流程与参数配置，暂不支持实际发起任务。
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
                答辩建议仅供准备和演练参考，不替代导师指导与学校正式评审要求。
                <a href="javascript:void(0)">详情&gt;&gt;</a>
                <a href="javascript:void(0)">相关报道&gt;&gt;</a>
              </section>
              <section class="aigc-side__hero">
                <img :src="defenseIllustration" alt="答辩服务流程图" />
              </section>
              <section class="aigc-side__brand">
                <div class="aigc-side__brand-icon">
                  <img :src="defenseMark" alt="" />
                </div>
                <h3>答辩支持服务</h3>
              </section>
              <p class="aigc-side__intro">计划输出答辩问题预测、回答结构建议、PPT讲解节奏和高频追问应对卡片。</p>
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

import defenseMark from "../../assets/icons/defense-mark.svg"
import defenseIllustration from "../../assets/illustrations/defense-lab.svg"
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
const selectedStage = ref("proposal")
const dragActive = ref(false)
const paperFile = ref(null)
const form = reactive({
  focus: "",
})

const fieldErrors = reactive({
  paper: "",
})

const platformCards = [
  { value: "cnki", label: "格物学术标准答辩", desc: "更贴近学位论文答辩规范，突出研究框架与创新价值表达。" },
  { value: "vip", label: "格物学术专业答辩", desc: "更偏向期刊与项目成果展示，强调方法和结果可解释性。" },
  { value: "paperpass", label: "格物学术极速答辩", desc: "适合快速彩排与重点追问预演，节奏更紧凑。" },
]

const defenseStages = [
  { value: "proposal", label: "开题答辩" },
  { value: "midterm", label: "中期答辩" },
  { value: "pre", label: "预答辩" },
  { value: "final", label: "正式答辩" },
]

onMounted(async () => {
  if (getUserToken()) {
    await refreshUser()
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
  if (![".docx", ".pdf", ".ppt", ".pptx"].includes(ext)) {
    fieldErrors.paper = "仅支持 .docx / .pdf / .ppt / .pptx 文件"
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
