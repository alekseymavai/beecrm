import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: AppLayout,
            children: [
                {
                    path: '/',
                    redirect: '/orders'
                },
                {
                    path: '/orders',
                    name: 'orders',
                    component: () => import('@/views/beecrm/OrdersView.vue')
                },
                {
                    path: '/orders/:id',
                    name: 'order-detail',
                    component: () => import('@/views/beecrm/OrderDetailView.vue'),
                    props: true
                },
                {
                    path: '/clients',
                    name: 'clients',
                    component: () => import('@/views/beecrm/ClientsView.vue')
                },
                {
                    path: '/clients/:id',
                    name: 'client-detail',
                    component: () => import('@/views/beecrm/ClientDetailView.vue'),
                    props: true
                }
            ]
        },
        {
            path: '/pages/notfound',
            name: 'notfound',
            component: () => import('@/views/pages/NotFound.vue')
        }
    ]
});

export default router;
