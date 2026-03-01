import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import 'bootstrap/dist/css/bootstrap.min.css'
import { AVPlugin } from "vue-audio-visual";

const app = createApp(App)
app.use(router)
app.use(AVPlugin);
app.mount('#app')
