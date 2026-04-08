<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

const titles = {
    '/orders': 'Заказы',
    '/clients': 'Клиенты',
};

const title = computed(() => {
    for (const [prefix, label] of Object.entries(titles)) {
        if (route.path.startsWith(prefix)) return label;
    }
    return 'BEECRM';
});
</script>

<template>
    <header class="app-topbar">
        <span class="app-topbar__title">{{ title }}</span>
    </header>
</template>
