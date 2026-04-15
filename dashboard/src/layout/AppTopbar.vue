<script setup>
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.js';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const SECTION = { '/orders': 'Заказы', '/clients': 'Клиенты', '/products': 'Товары' };

const breadcrumbs = computed(() => {
    const path = route.path;
    if (path === '/') return [{ label: 'Главная', to: '/', last: true }];

    const section = Object.keys(SECTION).find(k => path.startsWith(k));
    if (!section) return [{ label: 'BEECRM', to: '/', last: true }];

    const parts = [{ label: SECTION[section], to: section, last: path === section }];
    if (path !== section) {
        const id = path.replace(section + '/', '');
        parts.push({ label: `#${id}`, to: path, last: true });
    }
    return [{ label: 'Главная', to: '/', last: false }, ...parts];
});
</script>

<template>
    <header class="topbar">
        <!-- Breadcrumb -->
        <nav class="topbar-breadcrumb">
            <template v-for="(crumb, idx) in breadcrumbs" :key="crumb.to">
                <span v-if="idx > 0" class="topbar-sep">/</span>
                <button
                    v-if="!crumb.last"
                    class="topbar-crumb topbar-crumb--link"
                    @click="router.push(crumb.to)"
                >{{ crumb.label }}</button>
                <span v-else class="topbar-crumb topbar-crumb--current">{{ crumb.label }}</span>
            </template>
        </nav>

        <!-- Actions -->
        <div class="topbar-actions">
            <button class="topbar-icon-btn" title="Уведомления">
                <i class="pi pi-bell"></i>
            </button>
            <div class="topbar-divider"></div>
            <div class="topbar-avatar">{{ (auth.username || 'U')[0].toUpperCase() }}</div>
        </div>
    </header>
</template>
