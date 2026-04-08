<script setup>
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.js';

const router = useRouter();
const auth = useAuthStore();

const items = [
    { label: 'Главная',  icon: 'pi pi-chart-bar',    to: '/' },
    { label: 'Заказы',   icon: 'pi pi-shopping-cart', to: '/orders' },
    { label: 'Клиенты',  icon: 'pi pi-users',         to: '/clients' },
    { label: 'Товары',   icon: 'pi pi-tag',           to: '/products' },
];

function logout() {
    auth.logout();
    router.push('/login');
}
</script>

<template>
    <aside class="app-sidebar">
        <div class="app-sidebar__logo">BEECRM</div>
        <nav class="app-sidebar__nav">
            <RouterLink
                v-for="item in items"
                :key="item.to"
                :to="item.to"
                class="nav-item"
                :class="{ active: $route.path === item.to || ($route.path.startsWith(item.to) && item.to !== '/') }"
                custom
                v-slot="{ navigate }"
            >
                <a @click="navigate" class="nav-item" :class="{ active: $route.path === item.to || ($route.path.startsWith(item.to) && item.to !== '/') }">
                    <i :class="item.icon" />
                    {{ item.label }}
                </a>
            </RouterLink>
        </nav>
        <div class="app-sidebar__footer">
            <button class="nav-item nav-item--logout" @click="logout">
                <i class="pi pi-sign-out" />
                Выйти
            </button>
        </div>
    </aside>
</template>
