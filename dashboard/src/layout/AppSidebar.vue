<script setup>
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.js';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const nav = [
    {
        section: 'Аналитика',
        items: [
            { label: 'Главная', icon: 'pi-chart-bar', to: '/' },
        ],
    },
    {
        section: 'Управление',
        items: [
            { label: 'Заказы',  icon: 'pi-shopping-cart', to: '/orders' },
            { label: 'Клиенты', icon: 'pi-users',         to: '/clients' },
            { label: 'Товары',  icon: 'pi-tag',           to: '/products' },
        ],
    },
];

function isActive(to) {
    if (to === '/') return route.path === '/';
    return route.path.startsWith(to);
}

function go(to) { router.push(to); }

function logout() {
    auth.logout();
    router.push('/login');
}
</script>

<template>
    <aside class="sidebar">
        <!-- Logo -->
        <div class="sidebar-logo">
            <div class="sidebar-logo-icon">
                <i class="pi pi-database" style="font-size:14px"></i>
            </div>
            <span class="sidebar-logo-text">
                <span class="sidebar-logo-bee">BEE</span><span class="sidebar-logo-crm">CRM</span>
            </span>
        </div>

        <!-- Nav -->
        <nav class="sidebar-nav">
            <template v-for="group in nav" :key="group.section">
                <div class="sidebar-section">{{ group.section }}</div>
                <button
                    v-for="item in group.items"
                    :key="item.to"
                    :class="['sidebar-item', { 'sidebar-item--active': isActive(item.to) }]"
                    @click="go(item.to)"
                >
                    <span class="sidebar-item-icon">
                        <i :class="['pi', item.icon]"></i>
                    </span>
                    <span class="sidebar-item-label">{{ item.label }}</span>
                </button>
            </template>
        </nav>

        <!-- Footer -->
        <div class="sidebar-footer">
            <div class="sidebar-user">
                <div class="sidebar-avatar">{{ (auth.username || 'U')[0].toUpperCase() }}</div>
                <div class="sidebar-user-info">
                    <div class="sidebar-user-name">{{ auth.username || 'Пользователь' }}</div>
                    <div class="sidebar-user-role">{{ auth.role || 'Менеджер' }}</div>
                </div>
            </div>
            <button class="sidebar-logout" @click="logout">
                <i class="pi pi-sign-out"></i>
                Выйти
            </button>
        </div>
    </aside>
</template>
