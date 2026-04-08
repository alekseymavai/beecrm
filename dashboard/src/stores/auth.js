import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import http from '@/api/http.js';

export const useAuthStore = defineStore('auth', () => {
    const KEY = 'beecrm_api_key';
    const apiKey = ref(localStorage.getItem(KEY) || '');
    const loading = ref(false);
    const error = ref(null);

    const isLoggedIn = computed(() => !!apiKey.value);

    async function login(key) {
        loading.value = true;
        error.value = null;
        localStorage.setItem(KEY, key);
        apiKey.value = key;
        try {
            await http.get('/health');
        } catch (e) {
            localStorage.removeItem(KEY);
            apiKey.value = '';
            error.value = 'Неверный ключ доступа';
            throw e;
        } finally {
            loading.value = false;
        }
    }

    function logout() {
        apiKey.value = '';
        localStorage.removeItem(KEY);
    }

    return { apiKey, isLoggedIn, loading, error, login, logout };
});
