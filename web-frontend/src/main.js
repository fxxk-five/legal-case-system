import { createApp } from 'vue'
import { ElLoadingDirective } from 'element-plus/es/components/loading/index'
import 'element-plus/es/components/loading/style/css'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'

import App from './App.vue'
import router from './router'
import pinia from './stores'
import './style.css'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.directive('loading', ElLoadingDirective)
app.mount('#app')
