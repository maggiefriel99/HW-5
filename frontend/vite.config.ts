import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend (FastAPI on :8000) allows this origin via CORS.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
