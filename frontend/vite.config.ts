import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server mirrors nginx in production: /api is proxied to the backend, so the app also works
// when opened from another device (e.g. over Tailscale) during `npm run dev`.
const apiProxy = {
  "/api": { target: "http://localhost:8000", changeOrigin: true },
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: apiProxy,
  },
  preview: {
    host: true,
    port: 5173,
    proxy: apiProxy,
  },
});
