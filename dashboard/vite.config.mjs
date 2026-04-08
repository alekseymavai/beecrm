import { fileURLToPath, URL } from 'node:url';
import { PrimeVueResolver } from '@primevue/auto-import-resolver';
import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { defineConfig } from 'vite';

export default defineConfig({
    plugins: [
        vue(),
        tailwindcss(),
        Components({ resolvers: [PrimeVueResolver()] }),
    ],
    resolve: {
        alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
        proxy: {
            '/api': {
                target: 'http://localhost:8001',
                rewrite: (path) => path.replace(/^\/api/, ''),
            },
        },
    },
});
