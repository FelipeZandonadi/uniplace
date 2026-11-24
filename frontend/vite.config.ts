import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const backend = { target: 'http://localhost:8000', changeOrigin: false };

// O access token vive em memória: um XSS seria sequestro de sessão. A CSP limita o estrago.
// Só no build: o dev server injeta script inline (React Refresh). frame-ancestors não funciona
// via <meta>; configure-o (e os demais headers) no servidor que hospedar o dist/.
const csp = "default-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'";

export default defineConfig({
  plugins: [react(), {
    name: 'csp',
    apply: 'build',
    transformIndexHtml: () => [{
      tag: 'meta',
      attrs: { 'http-equiv': 'Content-Security-Policy', content: csp },
      injectTo: 'head-prepend',
    }],
  }],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': backend, '/mock-sso': backend, '/media': backend, '/static': backend },
  },
});
