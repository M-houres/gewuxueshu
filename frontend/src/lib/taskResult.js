export function mapProcessingMode(mode) {
  if (mode === "LLM_PLUS_ALGO") return "大模型 + 算法"
  if (mode === "ALGO_ONLY") return "仅算法"
  return mode || "-"
}

export function taskResultSummary(task) {
  const result = task?.result_json || {}
  if (result.summary) return result.summary
  if (task?.task_type === "aigc_detect") return "检测已完成，可下载完整报告查看结果。"
  return "任务已完成，可下载结果文件继续人工复核。"
}

export function taskResultMetrics(task) {
  const result = task?.result_json || {}
  const metrics = []
  if (task?.task_type === "aigc_detect") {
    if (typeof result.score_pct === "number") metrics.push({ label: "AIGC分值", value: `${result.score_pct}%` })
    if (result.risk_band) metrics.push({ label: "风险等级", value: result.risk_band })
    if (result.source_stats?.char_count) metrics.push({ label: "字符数", value: result.source_stats.char_count })
    if (result.source_stats?.sentence_count) metrics.push({ label: "句子数", value: result.source_stats.sentence_count })
  } else {
    if (typeof result.change_ratio === "number") metrics.push({ label: "改动幅度", value: `${result.change_ratio}%` })
    if (result.source_stats?.char_count) metrics.push({ label: "原文字数", value: result.source_stats.char_count })
    if (result.output_stats?.char_count) metrics.push({ label: "结果字数", value: result.output_stats.char_count })
    if (result.report_summary?.available) metrics.push({ label: "辅助报告", value: "已参与分析" })
  }
  if (result.mode) metrics.push({ label: "处理模式", value: mapProcessingMode(result.mode) })
  if (typeof result.llm_used === "boolean") metrics.push({ label: "LLM", value: result.llm_used ? "已使用" : "未使用" })
  if (typeof result.algo_package_used === "boolean") metrics.push({ label: "算法包", value: result.algo_package_used ? "已使用" : "未使用" })
  return metrics
}

export function taskResultReportMetrics(task) {
  return task?.result_json?.report_summary?.metrics || []
}

export function taskResultRiskParagraphs(task) {
  return task?.result_json?.risk_paragraphs || []
}

export function taskResultReviewPoints(task) {
  return task?.result_json?.review_points || task?.result_json?.report_summary?.recommended_actions || []
}

export function taskResultOutputPreview(task) {
  return task?.result_json?.output_preview || ""
}
