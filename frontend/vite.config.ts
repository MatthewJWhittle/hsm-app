import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In Docker, set API_PROXY_TARGET=http://backend:8000 so the Vite dev server can reach the API.
const apiProxyTarget = process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    proxy: {
      // Matches production: Firebase Hosting rewrites `/api` → Cloud Run backend.
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
})
