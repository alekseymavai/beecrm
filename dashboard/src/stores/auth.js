import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import http from '@/api/http.js';

const TOKEN_KEY = 'beecrm_jwt';

function decodeJwt(token) {
    try {
        const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(base64));
    } catch {
        return null;
    }
}

export const useAuthStore = defineStore('auth', () => {
    const token = ref(localStorage.getItem(TOKEN_KEY) || '');
    const loading = ref(false);
    const error = ref(null);

    const decoded = computed(() => (token.value ? decodeJwt(token.value) : null));
    const isLoggedIn = computed(() => {
        if (!decoded.value) return false;
        return decoded.value.exp * 1000 > Date.now();
    });
    const username = computed(() => decoded.value?.sub ?? '');
    const role = computed(() => decoded.value?.role ?? '');

    async function login(loginVal, password) {
        loading.value = true;
        error.value = null;
        try {
            const { data } = await http.post('/auth/login', { login: loginVal, password });
            token.value = data.access_token;
            localStorage.setItem(TOKEN_KEY, data.access_token);
        } catch (e) {
            const status = e.response?.status;
            if (status === 401) error.value = 'Неверный логин или пароль';
            else if (status === 403) error.value = 'Аккаунт деактивирован';
            else error.value = 'Ошибка сервера';
            throw e;
        } finally {
            loading.value = false;
        }
    }

    async function register(loginVal, password) {
        loading.value = true;
        error.value = null;
        try {
            const { data } = await http.post('/auth/register', { login: loginVal, password });
            token.value = data.access_token;
            localStorage.setItem(TOKEN_KEY, data.access_token);
        } catch (e) {
            const status = e.response?.status;
            if (status === 409) error.value = 'Логин уже занят';
            else if (status === 422) error.value = 'Слишком короткий пароль (мин. 3 символа)';
            else error.value = 'Ошибка регистрации';
            throw e;
        } finally {
            loading.value = false;
        }
    }

    function logout() {
        token.value = '';
        localStorage.removeItem(TOKEN_KEY);
    }

    return { token, isLoggedIn, username, role, loading, error, login, register, logout };
});
