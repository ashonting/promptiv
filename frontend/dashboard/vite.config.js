// frontend/dashboard/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
//  base: '/',

  plugins: [react()],

  publicDir: 'public',

  build: {
    outDir: 'dist',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: 'index.html',
      output: {
        entryFileNames:  'assets/[name]-[hash].js',
        chunkFileNames:  'assets/[name]-[hash].js',
        assetFileNames:  'assets/[name]-[hash].[ext]',
      }
    }
  },

  server: {
    port: 5173,
    strictPort: true,
    open: false
  }
});
