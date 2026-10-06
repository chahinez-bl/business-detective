import { defineConfig, loadEnv } from "vite"
import react from "@vitejs/plugin-react"

// Production: the API URL is baked in at build time through VITE_API_URL (leave empty when the API serves this app on the same domain).
// Development: /api is proxied to the local backend (127.0.0.1 avoids IPv6 localhost issues).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  return {
    plugins: [react()],
    server: { port: 5173, proxy: { "/api": { target: env.DEV_API_PROXY || "http://127.0.0.1:8000", changeOrigin: true } } },
    build: { chunkSizeWarningLimit: 900 },
  }
})
