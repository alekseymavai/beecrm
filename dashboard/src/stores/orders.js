import { defineStore } from 'pinia';
import { ref } from 'vue';
import http from '@/api/http.js';

export const TRANSITIONS = {
    NEW: ['CONFIRMED', 'CANCELLED'],
    CONFIRMED: ['IN_PROGRESS', 'CANCELLED'],
    IN_PROGRESS: ['DONE', 'CANCELLED'],
    DONE: [],
    CANCELLED: []
};

export const STATUS_SEVERITY = {
    NEW: 'info',
    CONFIRMED: 'primary',
    IN_PROGRESS: 'warn',
    DONE: 'success',
    CANCELLED: 'danger'
};

export const SOURCE_LABEL = {
    UDS: 'UDS',
    MESSENGER: 'Мессенджер',
    TABLE: 'Таблица'
};

export const useOrdersStore = defineStore('orders', () => {
    const list = ref([]);
    const current = ref(null);
    const history = ref([]);
    const loading = ref(false);
    const error = ref(null);

    async function fetchAll(page = 1) {
        loading.value = true;
        error.value = null;
        try {
            const { data } = await http.get('/orders/', { params: { page, page_size: 100 } });
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
            const { data } = await http.get(`/orders/${id}`);
            current.value = data;
        } catch (e) {
            error.value = e.response?.data?.detail || e.message;
        } finally {
            loading.value = false;
        }
    }

    async function fetchHistory(id) {
        const { data } = await http.get(`/orders/${id}/history`);
        history.value = data;
    }

    async function updateStatus(id, status, actor = 'dashboard') {
        const { data } = await http.patch(`/orders/${id}/status`, { status, actor });
        const idx = list.value.findIndex((o) => o.id === Number(id));
        if (idx !== -1) list.value[idx] = data;
        current.value = data;
        return data;
    }

    async function importExcel(file) {
        const form = new FormData();
        form.append('file', file);
        const { data } = await http.post('/import/excel', form);
        return data;
    }

    function availableTransitions(status) {
        return TRANSITIONS[status] ?? [];
    }

    return { list, current, history, loading, error, fetchAll, fetchOne, fetchHistory, updateStatus, importExcel, availableTransitions };
});
