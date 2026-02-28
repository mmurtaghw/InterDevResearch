import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './src/App.vue'
import './global.css'
;(async () => {
  const app = createApp(App)

  app.use(ElementPlus)
  app.mount('#app')
})()
