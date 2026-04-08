<script setup>
import AppSidebar from './AppSidebar.vue';
import AppTopbar from './AppTopbar.vue';
</script>

<template>
    <AppSidebar />
    <AppTopbar />
    <main class="app-main">
        <router-view />
    </main>
    <Toast position="bottom-right" />
</template>
