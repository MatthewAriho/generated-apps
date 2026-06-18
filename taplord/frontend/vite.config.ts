import { defineConfig } from "vite";

export default defineConfig({
  base: "/",
  build: {
    outDir: "../nginx/dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
