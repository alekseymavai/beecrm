import { defineStore } from 'pinia';
import { ref } from 'vue';
import http from '@/api/http.js';

export const useClientsStore = defineStore('clients', () => {
    const list = ref([]);
    const current = ref(null);
    const history = ref([]);
    const loading = ref(false);
    const error = ref(null);

    async function fetchAll(page = 1) {
        loading.value = true;
        error.value = null;
        try {
            const { data } = await http.get('/clients/', { params: { page, page_size: 100 } });
            list.value = data;
        } catch (e) {
            error.value = e.response?.data?.detail || e.message;
        } finally {
            loading.value = false;
        }
    }

    async function fetchOne(id) {
        loading.value = true;
        error.value = null;
        try {
            const { data } = await http.get(`/clients/${id}`);
            current.value = data;
        } catch (e) {
            error.value = e.response?.data?.detail || e.message;
        } finally {
            loading.value = false;
        }
    }

    async function fetchHistory(id) {
        const { data } = await http.get(`/clients/${id}/history`);
        history.value = data;
    }

    async function create(payload) {
        const { data } = await http.post('/clients/', payload);
        list.value.unshift(data);
        return data;
    }

    async function update(id, payload) {
        const { data } = await http.patch(`/clients/${id}`, payload);
        const idx = list.value.findIndex((c) => c.id === Number(id));
        if (idx !== -1) list.value[idx] = data;
        current.value = data;
        return data;
    }

    return { list, current, history, loading, error, fetchAll, fetchOne, fetchHistory, create, update };
});
