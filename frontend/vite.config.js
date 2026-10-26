import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The FastAPI backend runs on 127.0.0.1:8000. In development Vite proxies the
// API and WebSocket traffic to it so the SPA can talk to the backend with
// same-origin relative URLs. In production the built `dist/` is served by
// FastAPI itself, so relative URLs keep working without any proxy.
const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/patients': { target: BACKEND, changeOrigin: true },
      '/doctors': { target: BACKEND, changeOrigin: true },
      '/triage': { target: BACKEND, changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
