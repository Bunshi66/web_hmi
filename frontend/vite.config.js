import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  envDir: '../',
  server: {
    proxy: {
      '/camera': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true
      },
      '/data': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
