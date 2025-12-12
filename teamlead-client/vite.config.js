import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://server:8000',
        changeOrigin: true,
        secure: false,
        logLevel: 'debug'
      },
      '/ws': {
        target: 'ws://server:8000', 
        changeOrigin: true,
        secure: false,
        ws: true,
        logLevel: 'debug'
      }
    }
  }
})
