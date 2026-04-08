<script setup>
const items = [
    { label: 'Заказы', icon: 'pi pi-shopping-cart', to: '/orders' },
    { label: 'Клиенты', icon: 'pi pi-users', to: '/clients' },
];
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
            >
                <i :class="item.icon" />
                {{ item.label }}
            </RouterLink>
        </nav>
    </aside>
</template>
