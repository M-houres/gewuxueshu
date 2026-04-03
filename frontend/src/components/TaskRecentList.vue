<template>
  <section class="scholar-panel">
    <div class="scholar-panel__header">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div class="scholar-kicker">近期任务</div>
          <h3 class="scholar-subtitle">{{ title }}</h3>
          <p v-if="description" class="scholar-lead">{{ description }}</p>
        </div>
        <button class="scholar-button scholar-button--secondary" type="button" @click="$emit('history')">
          进入个人中心
        </button>
      </div>
    </div>

    <div class="scholar-panel__body">
      <div v-if="guest" class="scholar-note">
        提交任务后，这里会自动同步最近记录。你可以先浏览流程，提交前再登录即可。
      </div>

      <div v-else-if="tasks.length === 0" class="scholar-empty">
        {{ emptyText }}
      </div>

      <div v-else class="scholar-list">
        <article v-for="item in tasks" :key="item.id" class="scholar-list-item">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="min-w-0 flex-1">
              <div class="truncate text-sm font-semibold text-[var(--ink)]">
                {{ item.source_filename || `任务 #${item.id}` }}
              </div>
              <div class="mt-3 flex flex-wrap gap-2">
                <span class="scholar-pill">{{ platformLabel(item.platform) }}</span>
                <span class="scholar-pill">{{ formatTime(item.created_at) }}</span>
                <span class="scholar-pill">{{ item.char_count || 0 }} 字符</span>
                <span class="scholar-pill">{{ item.cost_credits || 0 }} 积分</span>
              </div>
              <div v-if="summaryText(item)" class="mt-3 text-sm leading-7 text-[var(--ink-soft)]">
                {{ summaryText(item) }}
              </div>
            </div>

            <span class="scholar-badge" :class="statusClass(item.status)">
              {{ statusLabel(item.status) }}
            </span>
          </div>
        </article>
      </div>

      <div v-if="guest" class="scholar-inline-actions" style="margin-top: 14px">
        <button class="scholar-button" type="button" @click="$emit('login')">登录后同步</button>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, default: "近期任务" },
  description: { type: String, default: "" },
  tasks: { type: Array, default: () => [] },
  guest: { type: Boolean, default: false },
  emptyText: { type: String, default: "暂无任务记录" },
})

defineEmits(["history", "login"])

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}

function platformLabel(platform) {
  const mapping = {
    cnki: "仿知网检测",
    vip: "仿维普检测",
    paperpass: "仿PaperPass检测",
  }
  return mapping[platform] || platform || "-"
}

function statusLabel(status) {
  const mapping = {
    pending: "排队中",
    running: "处理中",
    completed: "已完成",
    failed: "失败",
  }
  return mapping[status] || status || "-"
}

function statusClass(status) {
  if (status === "completed") return "scholar-badge--success"
  if (status === "failed") return "scholar-badge--danger"
  if (status === "running") return "scholar-badge--info"
  return "scholar-badge--warn"
}

function summaryText(item) {
  if (item.status === "failed" && item.error_message) {
    return `失败原因：${item.error_message}`
  }
  if (item.task_type === "aigc_detect" && item.result_json?.ai_score != null) {
    const raw = Number(item.result_json.ai_score)
    const pct = raw <= 1 ? Math.round(raw * 100) : Math.round(raw)
    return `检测结果：AI 风险约 ${pct}%`
  }
  if (item.status === "completed") {
    return "任务已完成，可在个人中心查看完整摘要或下载结果文件。"
  }
  if (item.status === "running") {
    return "任务正在处理中，页面会按轮询状态自动同步最新进度。"
  }
  return "任务已创建，系统即将进入处理阶段。"
}
</script>
