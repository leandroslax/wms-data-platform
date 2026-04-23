import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/chat": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/metadata": "http://localhost:8000",
      "/orders": "http://localhost:8000",
      "/movements": "http://localhost:8000",
      "/inventory": "http://localhost:8000"
    }
  }
});
