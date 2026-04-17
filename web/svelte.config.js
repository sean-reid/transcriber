import adapter from '@sveltejs/adapter-cloudflare';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter(),
    csp: {
      directives: {
        'default-src': ['self'],
        'img-src': ['self', 'data:', 'blob:'],
        'media-src': ['self', 'blob:', 'https://*.r2.cloudflarestorage.com', 'https://*.r2.dev'],
        'connect-src': ['self', 'https://*.r2.cloudflarestorage.com', 'https://*.r2.dev', 'https://*.modal.run'],
        'script-src': ['self'],
        'style-src': ['self', 'unsafe-inline'],
        'font-src': ['self', 'data:'],
        'object-src': ['none'],
        'base-uri': ['self'],
        'frame-ancestors': ['none']
      }
    }
  }
};

export default config;
