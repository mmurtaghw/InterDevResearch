import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue()],
    resolve: {
        extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json', '.vue'],
        alias: {
            // To make the @ import alias work like in Vue CLI, we need to add this.
            '@': resolve(__dirname, './src'),
        },
    },
    server: {
        proxy: {
            '/api': {
                target: 'https://gutget.adaptcentre.ie', // Target API server
                changeOrigin: true, // Allow cross-origin
                secure: false, // Ignore https certificate issues (if any)
                rewrite: (path) => path.replace(/^\/api/, '') // Remove `/api` prefix
            },
            '/apiBooks': {
                target: 'http://localhost:2600', // Target API server, 
                changeOrigin: true,
                secure: false,
                rewrite: (path) => path.replace(/^\/apiBooks/, '')
            }
        }
    }
})
