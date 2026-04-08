<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useOrdersStore, SOURCE_LABEL } from '@/stores/orders.js';

const router = useRouter();
const toast = useToast();
const store = useOrdersStore();

const importLoading = ref(false);
const page = ref(1);
const PAGE_SIZE = 20;

const STATUS_LABEL = { NEW: 'Новый', CONFIRMED: 'Подтверждён', IN_PROGRESS: 'В работе', DONE: 'Выполнен', CANCELLED: 'Отменён' };
const STATUS_CLASS = { NEW: 'badge-new', CONFIRMED: 'badge-confirmed', IN_PROGRESS: 'badge-in_progress', DONE: 'badge-done', CANCELLED: 'badge-cancelled' };

onMounted(() => store.fetchAll());

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

async function onImport(event) {
    const file = event.files?.[0];
    if (!file) return;
    importLoading.value = true;
    try {
        const result = await store.importExcel(file);
        toast.add({ severity: 'success', summary: 'Импорт завершён', detail: `Создано: ${result.created}, ошибок: ${result.errors?.length ?? 0}`, life: 4000 });
        await store.fetchAll();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Ошибка импорта', detail: e.response?.data?.detail || e.message, life: 5000 });
    } finally {
        importLoading.value = false;
    }
}

const total = computed(() => store.list.length);
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));
const rows = computed(() => store.list.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE));
const pageNums = computed(() => {
    const all = Array.from({ length: totalPages.value }, (_, i) => i + 1);
    if (all.length <= 7) return all;
    const cur = page.value;
    const set = new Set([1, totalPages.value, cur, cur - 1, cur + 1].filter(p => p >= 1 && p <= totalPages.value));
    return [...set].sort((a, b) => a - b);
});
</script>

<template>
    <div class="card">
        <div class="page-header">
            <span class="page-title">Заказы</span>
            <FileUpload
                mode="basic"
                accept=".xlsx,.xls,.csv"
                :auto="true"
                chooseLabel="Импорт Excel"
                chooseIcon="pi pi-upload"
                :maxFileSize="10000000"
                :disabled="importLoading"
                @select="onImport"
            />
        </div>

        <Message v-if="store.error" severity="error" class="mb-3">{{ store.error }}</Message>

        <div class="tbl-wrap">
            <table class="tbl">
                <thead>
                    <tr>
                        <th style="width:70px">ID</th>
                        <th style="width:100px">Клиент</th>
                        <th style="width:130px">Источник</th>
                        <th style="width:160px">Статус</th>
                        <th>Создан</th>
                        <th style="width:44px"></th>
                    </tr>
                </thead>
                <tbody>
                    <template v-if="store.loading">
                        <tr v-for="i in 8" :key="i">
                            <td><div class="skel" style="width:36px"></div></td>
                            <td><div class="skel" style="width:54px"></div></td>
                            <td><div class="skel" style="width:72px"></div></td>
                            <td><div class="skel" style="width:88px"></div></td>
                            <td><div class="skel" style="width:110px"></div></td>
                            <td></td>
                        </tr>
                    </template>
                    <tr v-else-if="rows.length === 0">
                        <td colspan="6" class="tbl-empty">Нет заказов</td>
                    </tr>
                    <tr v-else v-for="row in rows" :key="row.id" class="clickable" @click="router.push(`/orders/${row.id}`)">
                        <td style="color:#94a3b8;font-size:13px">#{{ row.id }}</td>
                        <td>{{ row.client_id ?? '—' }}</td>
                        <td>{{ SOURCE_LABEL[row.source] ?? row.source ?? '—' }}</td>
                        <td>
                            <span :class="['badge', STATUS_CLASS[row.status] ?? 'badge-inactive']">
                                {{ STATUS_LABEL[row.status] ?? row.status }}
                            </span>
                        </td>
                        <td style="color:#64748b;font-size:13px">{{ formatDate(row.created_at) }}</td>
                        <td>
                            <button class="row-action" @click.stop="router.push(`/orders/${row.id}`)">
                                <i class="pi pi-arrow-right" style="font-size:12px"></i>
                            </button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div v-if="!store.loading && total > PAGE_SIZE" class="tbl-pager">
            <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} из {{ total }}</span>
            <div class="tbl-pager-btns">
                <button class="tbl-pager-btn" :disabled="page === 1" @click="page--">
                    <i class="pi pi-chevron-left" style="font-size:11px"></i>
                </button>
                <template v-for="(p, idx) in pageNums" :key="p">
                    <span v-if="idx > 0 && p - pageNums[idx-1] > 1" style="padding:0 4px;color:#cbd5e1">…</span>
                    <button :class="['tbl-pager-btn', { active: p === page }]" @click="page = p">{{ p }}</button>
                </template>
                <button class="tbl-pager-btn" :disabled="page === totalPages" @click="page++">
                    <i class="pi pi-chevron-right" style="font-size:11px"></i>
                </button>
            </div>
        </div>
    </div>
</template>
