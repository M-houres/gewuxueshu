import fs from "node:fs"
import fsp from "node:fs/promises"
import http from "node:http"
import https from "node:https"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const port = Number(process.env.PREVIEW_PORT || 5188)
const apiBase = process.env.PREVIEW_API_BASE || "http://127.0.0.1:8100"
const distDir = path.resolve(process.env.PREVIEW_DIST || path.join(__dirname, "..", "frontend", "dist"))

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
}

function send(res, status, headers, body) {
  res.writeHead(status, headers)
  res.end(body)
}

async function serveStatic(req, res) {
  const cleanPath = decodeURIComponent((req.url || "/").split("?")[0].split("#")[0])
  const relativePath = cleanPath === "/" ? "index.html" : cleanPath.replace(/^\/+/, "")
  let targetPath = path.resolve(distDir, relativePath)
  if (!targetPath.startsWith(distDir)) {
    send(res, 403, { "Content-Type": "text/plain; charset=utf-8" }, "Forbidden")
    return
  }

  try {
    const stat = await fsp.stat(targetPath)
    if (stat.isDirectory()) {
      targetPath = path.join(targetPath, "index.html")
    }
  } catch {
    targetPath = path.join(distDir, "index.html")
  }

  try {
    const content = await fsp.readFile(targetPath)
    const ext = path.extname(targetPath).toLowerCase()
    send(
      res,
      200,
      {
        "Content-Type": mimeTypes[ext] || "application/octet-stream",
        "Content-Length": content.length,
      },
      req.method === "HEAD" ? "" : content
    )
  } catch {
    send(res, 404, { "Content-Type": "text/plain; charset=utf-8" }, "Not Found")
  }
}

function proxyApi(req, res) {
  const target = new URL(req.url, apiBase)
  const client = target.protocol === "https:" ? https : http
  const proxyReq = client.request(
    target,
    {
      method: req.method,
      headers: {
        ...req.headers,
        host: target.host,
      },
    },
    (proxyRes) => {
      const headers = { ...proxyRes.headers }
      delete headers["content-encoding"]
      delete headers["transfer-encoding"]
      res.writeHead(proxyRes.statusCode || 502, headers)
      proxyRes.pipe(res)
    }
  )

  proxyReq.on("error", (error) => {
    send(
      res,
      502,
      { "Content-Type": "text/plain; charset=utf-8" },
      `Backend unavailable: ${error.message}`
    )
  })

  req.pipe(proxyReq)
}

const server = http.createServer(async (req, res) => {
  if ((req.url || "").startsWith("/api/v1")) {
    proxyApi(req, res)
    return
  }
  await serveStatic(req, res)
})

server.listen(port, "127.0.0.1", () => {
  console.log(`Preview server running at http://127.0.0.1:${port}`)
  console.log(`Static dir: ${distDir}`)
  console.log(`API base: ${apiBase}`)
})

process.on("SIGTERM", () => server.close())
process.on("SIGINT", () => server.close())
