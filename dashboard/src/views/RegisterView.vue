<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.js';

const router = useRouter();
const auth = useAuthStore();
const login = ref('');
const password = ref('');
const confirm = ref('');
const localError = ref('');

async function submit() {
    localError.value = '';
    if (!login.value.trim()) { localError.value = 'Введите логин'; return; }
    if (password.value.length < 3) { localError.value = 'Пароль — минимум 3 символа'; return; }
    if (password.value !== confirm.value) { localError.value = 'Пароли не совпадают'; return; }
    try {
        await auth.register(login.value.trim(), password.value);
        router.push('/');
    } catch {}
}

const errorMsg = () => localError.value || auth.error;
</script>

<template>
    <div class="login-page">
        <div class="login-box">
            <div class="login-logo">BEECRM</div>
            <div class="login-title">Регистрация</div>

            <div class="login-field">
                <label>Логин</label>
                <InputText
                    v-model="login"
                    placeholder="Придумайте логин"
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
                    placeholder="Минимум 3 символа"
                    class="w-full"
                    autocomplete="new-password"
                    @keyup.enter="submit"
                />
            </div>

            <div class="login-field" style="margin-top:12px">
                <label>Подтвердить пароль</label>
                <InputText
                    v-model="confirm"
                    type="password"
                    placeholder="Повторите пароль"
                    class="w-full"
                    autocomplete="new-password"
                    @keyup.enter="submit"
                />
            </div>

            <Message v-if="errorMsg()" severity="error" class="mt-2">{{ errorMsg() }}</Message>

            <Button
                label="Зарегистрироваться"
                :loading="auth.loading"
                class="w-full mt-3"
                @click="submit"
            />

            <div style="text-align:center; margin-top:16px">
                <button class="btn-link" @click="$router.push('/login')">
                    Уже есть аккаунт? Войти
                </button>
            </div>
        </div>
    </div>
</template>
