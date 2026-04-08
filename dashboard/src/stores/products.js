import { defineStore } from 'pinia';
import { ref } from 'vue';
import http from '@/api/http.js';

export const useProductsStore = defineStore('products', () => {
    const list = ref([]);
    const current = ref(null);
    const loading = ref(false);
    const error = ref(null);

    async function fetchAll(page = 1) {
        loading.value = true;
        error.value = null;
        try {
            const { data } = await http.get('/products/', { params: { page, page_size: 100 } });
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
            const { data } = await http.get(`/products/${id}`);
            current.value = data;
        } catch (e) {
            error.value = e.response?.data?.detail || e.message;
        } finally {
            loading.value = false;
        }
    }

    async function create(payload) {
        const { data } = await http.post('/products/', payload);
        list.value.unshift(data);
        return data;
    }

    async function update(id, payload) {
        const { data } = await http.patch(`/products/${id}`, payload);
        current.value = data;
        const idx = list.value.findIndex(p => p.id === Number(id));
        if (idx !== -1) list.value[idx] = data;
        return data;
    }

    async function remove(id) {
        await http.delete(`/products/${id}`);
        list.value = list.value.filter(p => p.id !== id);
    }

    return { list, current, loading, error, fetchAll, fetchOne, create, update, remove };
});
