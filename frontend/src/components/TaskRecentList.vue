<template>
  <section class="rounded-2xl border border-[#d9dee4] bg-white p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div class="text-xs uppercase tracking-[0.16em] text-[#6e7a85]">Recent Tasks</div>
        <h3 class="mt-1 text-lg font-semibold text-[#16212b]">{{ title }}</h3>
        <p v-if="description" class="mt-1 text-sm text-[#5b6771]">{{ description }}</p>
      </div>
      <button class="rounded-xl bg-[#edf2f6] px-3 py-2 text-sm text-[#32414f]" @click="$emit('history')">
        查看全部
      </button>
    </div>

    <div v-if="guest" class="mt-4 rounded-2xl border border-[#dbe4ea] bg-[#f7fafc] p-4 text-sm text-[#556470]">
      <div class="font-medium text-[#314150]">游客模式下不展示个人任务记录</div>
      <div class="mt-1 leading-6">登录后可查看处理进度、失败原因和结果下载。</div>
      <button class="mt-3 rounded-xl bg-[#0f7a5f] px-4 py-2 text-sm text-white" @click="$emit('login')">
        登录后查看
      </button>
    </div>

    <div v-else-if="tasks.length === 0" class="mt-4 rounded-2xl border border-dashed border-[#d4dde4] bg-[#fafcfd] p-6 text-sm text-[#61707b]">
      {{ emptyText }}
    </div>

    <div v-else class="mt-4 space-y-3">
      <article
        v-for="item in tasks"
        :key="item.id"
        class="rounded-2xl border border-[#e3e8ed] bg-[linear-gradient(180deg,#ffffff,#f7fafc)] p-4"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="truncate text-sm font-semibold text-[#15212b]">
              {{ item.source_filename || `任务 #${item.id}` }}
            </div>
            <div class="mt-2 flex flex-wrap gap-2 text-xs text-[#61707b]">
              <span class="rounded-full bg-[#eef3f7] px-2 py-1">{{ platformLabel(item.platform) }}</span>
              <span class="rounded-full bg-[#eef3f7] px-2 py-1">{{ formatTime(item.created_at) }}</span>
              <span class="rounded-full bg-[#eef3f7] px-2 py-1">{{ item.char_count || 0 }} 字符</span>
              <span class="rounded-full bg-[#eef3f7] px-2 py-1">{{ item.cost_credits || 0 }} 积分</span>
            </div>
            <div v-if="summaryText(item)" class="mt-3 text-sm text-[#495864]">
              {{ summaryText(item) }}
            </div>
          </div>
          <span :class="statusClass(item.status)" class="inline-flex rounded-full border px-3 py-1 text-xs font-medium">
            {{ statusLabel(item.status) }}
          </span>
        </div>
      </article>
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
    cnki: "知网 CNKI",
    vip: "维普 VIP",
    paperpass: "PaperPass",
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
  if (status === "completed") return "border-[#cce6d8] bg-[#e9f6ef] text-[#11684e]"
  if (status === "failed") return "border-[#f3cdc8] bg-[#fff0ee] text-[#a33a33]"
  if (status === "running") return "border-[#d6e5f6] bg-[#eef5ff] text-[#1c5fa7]"
  return "border-[#ecdcb6] bg-[#fff5df] text-[#8a6117]"
}

function summaryText(item) {
  if (item.status === "failed" && item.error_message) {
    return `失败原因：${item.error_message}`
  }
  if (item.task_type === "aigc_detect" && item.result_json?.ai_score != null) {
    const raw = Number(item.result_json.ai_score)
    const pct = raw <= 1 ? Math.round(raw * 100) : Math.round(raw)
    return `检测结果：AI 率约 ${pct}%`
  }
  if (item.status === "completed") {
    return "任务处理完成，可前往历史记录查看详情或下载结果。"
  }
  if (item.status === "running") {
    return "任务正在处理中，页面刷新后状态会自动从后端同步。"
  }
  return "任务已创建，系统会继续处理。"
}
</script>
