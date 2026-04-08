import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';

export default createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: AppLayout,
            children: [
                { path: '', redirect: '/orders' },
                { path: 'orders', component: () => import('@/views/OrdersView.vue') },
                { path: 'orders/:id', component: () => import('@/views/OrderDetailView.vue'), props: true },
                { path: 'clients', component: () => import('@/views/ClientsView.vue') },
                { path: 'clients/:id', component: () => import('@/views/ClientDetailView.vue'), props: true },
            ],
        },
    ],
});
