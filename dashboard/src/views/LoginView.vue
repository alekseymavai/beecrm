<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.js';

const router = useRouter();
const auth = useAuthStore();
const login = ref('');
const password = ref('');

async function submit() {
    if (!login.value.trim() || !password.value) return;
    try {
        await auth.login(login.value.trim(), password.value);
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
                <label>Логин</label>
                <InputText
                    v-model="login"
                    placeholder="Введите логин"
                    class="w-full"
                    autocomplete="username"
                    @keyup.enter="submit"
                />
            </div>

            <div class="login-field" style="margin-top:12px">
                <label>Пароль</label>
                <InputText
                    v-model="password"
                    type="password"
                    placeholder="Введите пароль"
                    class="w-full"
                    autocomplete="current-password"
                    @keyup.enter="submit"
                />
            </div>

            <Message v-if="auth.error" severity="error" class="mt-2">{{ auth.error }}</Message>

            <Button
                label="Войти"
                :loading="auth.loading"
                class="w-full mt-3"
                @click="submit"
            />

            <div style="text-align:center; margin-top:16px">
                <button class="btn-link" @click="$router.push('/register')">
                    Нет аккаунта? Зарегистрироваться
                </button>
            </div>
        </div>
    </div>
</template>
