<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.js';

const router = useRouter();
const auth = useAuthStore();
const key = ref('');

async function submit() {
    if (!key.value.trim()) return;
    try {
        await auth.login(key.value.trim());
        router.push('/');
    } catch {}
}
</script>

<template>
    <div class="login-page">
        <div class="login-box">
            <div class="login-logo">BEECRM</div>
            <div class="login-title">Вход в систему</div>
            <div class="login-field">
                <label>API ключ</label>
                <InputText v-model="key" type="password" placeholder="Введите ключ доступа" class="w-full" @keyup.enter="submit" />
            </div>
            <Message v-if="auth.error" severity="error" class="mt-2">{{ auth.error }}</Message>
            <Button label="Войти" :loading="auth.loading" class="w-full mt-3" @click="submit" />
        </div>
    </div>
</template>
