import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: '/login', component: () => import('@/views/LoginView.vue') },
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
    if (to.path === '/login') return true;
    const key = localStorage.getItem('beecrm_api_key');
    if (!key) return '/login';
    return true;
});

export default router;
