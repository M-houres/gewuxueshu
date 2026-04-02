import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000"

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    proxy: {
      "/api/v1": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/echarts")) {
            return "vendor-echarts"
          }
          if (id.includes("node_modules/zrender")) {
            return "vendor-zrender"
          }
          return undefined
        },
      },
    },
  },
})
