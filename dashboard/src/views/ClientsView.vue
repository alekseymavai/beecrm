<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useClientsStore } from '@/stores/clients.js';

const router = useRouter();
const toast = useToast();
const store = useClientsStore();

const showDialog = ref(false);
const saving = ref(false);
const search = ref('');
const form = ref({ name: '', phone: '', email: '' });
const page = ref(1);
const PAGE_SIZE = 20;

onMounted(() => store.fetchAll());

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function openCreate() {
    form.value = { name: '', phone: '', email: '' };
    showDialog.value = true;
}

async function submit() {
    if (!form.value.phone && !form.value.email) {
        toast.add({ severity: 'warn', summary: 'Нужен телефон или email', life: 3000 });
        return;
    }
    saving.value = true;
    try {
        await store.create(form.value);
        showDialog.value = false;
        toast.add({ severity: 'success', summary: 'Клиент создан', life: 3000 });
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || e.message, life: 5000 });
    } finally {
        saving.value = false;
    }
}

const filtered = computed(() => {
    if (!search.value.trim()) return store.list;
    const q = search.value.toLowerCase();
    return store.list.filter(c =>
        (c.name ?? '').toLowerCase().includes(q) ||
        (c.phone ?? '').includes(q) ||
        (c.email ?? '').toLowerCase().includes(q)
    );
});

const total = computed(() => filtered.value.length);
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));
const rows = computed(() => filtered.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE));
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
            <span class="page-title">Клиенты</span>
            <div class="flex gap-2 items-center">
                <div class="search-box">
                    <i class="pi pi-search search-icon"></i>
                    <input v-model="search" class="search-input" placeholder="Поиск..." @input="page = 1" />
                </div>
                <button class="btn-primary" @click="openCreate">
                    <i class="pi pi-plus" style="font-size:11px"></i> Добавить
                </button>
            </div>
        </div>

        <Message v-if="store.error" severity="error" class="mb-3">{{ store.error }}</Message>

        <div class="tbl-wrap">
            <table class="tbl">
                <thead>
                    <tr>
                        <th style="width:70px">ID</th>
                        <th>Имя</th>
                        <th style="width:150px">Телефон</th>
                        <th>Email</th>
                        <th style="width:120px">Создан</th>
                        <th style="width:44px"></th>
                    </tr>
                </thead>
                <tbody>
                    <template v-if="store.loading">
                        <tr v-for="i in 8" :key="i">
                            <td><div class="skel" style="width:36px"></div></td>
                            <td><div class="skel" style="width:120px"></div></td>
                            <td><div class="skel" style="width:100px"></div></td>
                            <td><div class="skel" style="width:140px"></div></td>
                            <td><div class="skel" style="width:80px"></div></td>
                            <td></td>
                        </tr>
                    </template>
                    <tr v-else-if="rows.length === 0">
                        <td colspan="6" class="tbl-empty">Нет клиентов</td>
                    </tr>
                    <tr v-else v-for="row in rows" :key="row.id" class="clickable" @click="router.push(`/clients/${row.id}`)">
                        <td style="color:#94a3b8;font-size:13px">#{{ row.id }}</td>
                        <td style="font-weight:500">{{ row.name || '—' }}</td>
                        <td style="color:#64748b;font-size:13px">{{ row.phone || '—' }}</td>
                        <td style="color:#64748b;font-size:13px">{{ row.email || '—' }}</td>
                        <td style="color:#94a3b8;font-size:13px">{{ formatDate(row.created_at) }}</td>
                        <td>
                            <button class="row-action" @click.stop="router.push(`/clients/${row.id}`)">
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

    <Dialog v-model:visible="showDialog" header="Новый клиент" modal style="width: 400px">
        <div class="flex flex-col gap-3 mt-2">
            <div class="flex flex-col gap-1">
                <label class="text-sm font-medium">Имя</label>
                <InputText v-model="form.name" placeholder="Иван Иванов" />
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-sm font-medium">Телефон</label>
                <InputText v-model="form.phone" placeholder="+79001234567" />
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-sm font-medium">Email</label>
                <InputText v-model="form.email" placeholder="ivan@example.com" />
            </div>
        </div>
        <template #footer>
            <Button label="Отмена" text @click="showDialog = false" />
            <Button label="Создать" :loading="saving" @click="submit" />
        </template>
    </Dialog>
</template>
