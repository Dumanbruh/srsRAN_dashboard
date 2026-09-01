import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Only the built bundle is served from /static/spa/ (by Django). The dev
  // server mounts routes at the root so React Router's paths (/, /scenarios/,
  // /ai/, /login/) match window.location the same way they will in prod.
  base: command === 'build' ? '/static/spa/' : '/',
  build: {
    outDir: '../dashboard/static/spa',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/logout/': { target: 'http://localhost:8000', changeOrigin: true },
      '/login/': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // GET is served by Vite itself (Login.jsx, with HMR); any other
        // method (the actual credential POST) goes to real Django.
        bypass: (req) => { if (req.method === 'GET') return req.url },
      },
    },
  },
}))
