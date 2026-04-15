import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';

function isTokenValid() {
    const token = localStorage.getItem('beecrm_jwt');
    if (!token) return false;
    try {
        const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        return payload.exp * 1000 > Date.now();
    } catch {
        return false;
    }
}

const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: '/login', component: () => import('@/views/LoginView.vue') },
        { path: '/register', component: () => import('@/views/RegisterView.vue') },
        {
            path: '/',
            component: AppLayout,
            children: [
                { path: '', component: () => import('@/views/DashboardView.vue') },
                { path: 'orders', component: () => import('@/views/OrdersView.vue') },
                { path: 'orders/:id', component: () => import('@/views/OrderDetailView.vue'), props: true },
                { path: 'clients', component: () => import('@/views/ClientsView.vue') },
                { path: 'clients/:id', component: () => import('@/views/ClientDetailView.vue'), props: true },
                { path: 'products', component: () => import('@/views/ProductsView.vue') },
                { path: 'products/:id', component: () => import('@/views/ProductDetailView.vue'), props: true },
            ],
        },
    ],
});

router.beforeEach((to) => {
    if (to.path === '/login' || to.path === '/register') return true;
    if (!isTokenValid()) return '/login';
    return true;
});

export default router;
