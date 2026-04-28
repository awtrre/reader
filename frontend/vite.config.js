import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            // 👇 核心修改：去掉开头的限制，只要 URL 包含 /api/static/books/ 统统拦截
            urlPattern: /.*\/api\/static\/books\/.*/i,
            // 👇 改用 StaleWhileRevalidate，容错率更高
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'epub-chapters-cache',
              expiration: {
                maxEntries: 5000, 
                maxAgeSeconds: 60 * 60 * 24 * 30, // 保留 30 天
              },
              cacheableResponse: {
                // 👇 核心修改：增加 206 状态码（非常重要，解决分块传输不缓存的问题）
                statuses: [0, 200, 206]
              }
            }
          }
        ]
      }
    })
  ],
  build: {
    chunkSizeWarningLimit: 1500, 
    
    rollupOptions: {
      output: {
        // 2. 核心优化：手动拆分代码块 (manualChunks)
        manualChunks(id) {
          // 只要是 node_modules 里的第三方依赖，就进行处理
          if (id.includes('node_modules')) {
            // 特别关照电子书引擎：把 epubjs 独立打包成一个文件，因为它的核心代码很大且极少变动
            if (id.includes('epubjs')) {
              return 'epubjs-core';
            }
            // 特别关照 Vue 核心库
            if (id.includes('vue')) {
              return 'vue-core';
            }
            // 剩下的所有第三方杂项（比如 Tailwind 工具等），统统塞进 vendor 里
            return 'vendor';
          }
        }
      }
    }
  }
})