function decodeMaybe(value) {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function inferExtensionFromType(contentType = "") {
  const type = String(contentType).toLowerCase()
  if (type.includes("application/pdf")) return ".pdf"
  if (type.includes("application/vnd.openxmlformats-officedocument.wordprocessingml.document")) return ".docx"
  if (type.includes("text/plain")) return ".txt"
  if (type.includes("text/csv")) return ".csv"
  if (type.includes("application/zip")) return ".zip"
  return ""
}

export function resolveDownloadFilename(response, fallback = "download") {
  const headers = response?.headers || {}
  const disposition = headers["content-disposition"] || headers["Content-Disposition"] || ""
  let filename = ""

  const starMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (starMatch?.[1]) {
    filename = decodeMaybe(starMatch[1].trim())
  }

  if (!filename) {
    const plainMatch = disposition.match(/filename="?([^\";]+)"?/i)
    if (plainMatch?.[1]) {
      filename = plainMatch[1].trim()
    }
  }

  if (!filename) {
    filename = fallback
  }

  if (!/\.[a-z0-9]{2,8}$/i.test(filename)) {
    const ext = inferExtensionFromType(headers["content-type"] || headers["Content-Type"])
    if (ext) {
      filename += ext
    }
  }
  return filename
}

export function triggerBlobDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export function downloadAxiosBlobResponse(response, fallback = "download") {
  const contentType = response?.headers?.["content-type"] || "application/octet-stream"
  const data = response?.data
  const blob = data instanceof Blob ? data : new Blob([data], { type: contentType })
  const filename = resolveDownloadFilename(response, fallback)
  triggerBlobDownload(blob, filename)
}

