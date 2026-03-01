import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import editingView from './views/editingView.vue'
import login from './views/login.vue'
import Myprojects from './views/myprojects.vue'


const routes = [
  { path: '/', component: Home },
  { path: '/home', component: Home },
  { path: '/editor', name: 'video-player',component: editingView},
  { path: '/login', component: login},
  { path: '/myprojects', component: Myprojects}
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router