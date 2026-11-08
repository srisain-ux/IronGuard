import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  optimizeDeps: { exclude: ["onnxruntime-web", "@huggingface/transformers"] },
  server: { port: 5173, strictPort: true },
});
