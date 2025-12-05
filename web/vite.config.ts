import path from "node:path";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/web/",
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    // 代码拆分优化
    rollupOptions: {
      output: {
        assetFileNames: "assets/[name]-[hash][extname]",
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js",
        // 手动拆分代码块
        manualChunks: {
          // React 核心
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          // UI 组件库
          "ui-vendor": [
            "@radix-ui/react-dialog",
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-select",
            "@radix-ui/react-tabs",
            "@radix-ui/react-toast",
            "@radix-ui/react-scroll-area",
            "@radix-ui/react-avatar",
            "@radix-ui/react-label",
            "@radix-ui/react-switch",
            "@radix-ui/react-separator",
            "@radix-ui/react-slot",
            "@radix-ui/react-alert-dialog",
          ],
          // 数据处理和状态管理
          "data-vendor": ["@tanstack/react-query", "zustand", "axios", "zod"],
          // Markdown 渲染
          markdown: ["react-markdown", "remark-gfm", "rehype-highlight"],
          // 国际化
          i18n: ["i18next", "react-i18next", "i18next-browser-languagedetector", "i18next-http-backend"],
        },
      },
    },
    // 调整 chunk 大小警告阈值
    chunkSizeWarningLimit: 1000,
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
