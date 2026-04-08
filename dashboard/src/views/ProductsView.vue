<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useProductsStore } from '@/stores/products.js';

const router = useRouter();
const toast = useToast();
const store = useProductsStore();

const showDialog = ref(false);
const saving = ref(false);
const search = ref('');
const form = ref({ name: '', price: 0, category: '', stock: 0, active: true, description: '' });
const page = ref(1);
const PAGE_SIZE = 20;

onMounted(() => store.fetchAll());

const filtered = computed(() => {
    if (!search.value.trim()) return store.list;
    const q = search.value.toLowerCase();
    return store.list.filter(p =>
        (p.name ?? '').toLowerCase().includes(q) ||
        (p.category ?? '').toLowerCase().includes(q)
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

function formatPrice(v) {
    return Number(v || 0).toLocaleString('ru-RU') + ' ₽';
}

function openCreate() {
    form.value = { name: '', price: 0, category: '', stock: 0, active: true, description: '' };
    showDialog.value = true;
}

async function submit() {
    if (!form.value.name.trim()) {
        toast.add({ severity: 'warn', summary: 'Введите название', life: 3000 });
        return;
    }
    saving.value = true;
    try {
        await store.create(form.value);
        showDialog.value = false;
        toast.add({ severity: 'success', summary: 'Товар создан', life: 3000 });
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || e.message, life: 5000 });
    } finally {
        saving.value = false;
    }
}
</script>

<template>
    <div class="card">
        <div class="page-header">
            <span class="page-title">Товары</span>
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
                        <th>Название</th>
                        <th style="width:140px">Категория</th>
                        <th style="width:110px">Цена</th>
                        <th style="width:90px">Остаток</th>
                        <th style="width:90px">Статус</th>
                        <th style="width:44px"></th>
                    </tr>
                </thead>
                <tbody>
                    <template v-if="store.loading">
                        <tr v-for="i in 6" :key="i">
                            <td><div class="skel" style="width:36px"></div></td>
                            <td><div class="skel" style="width:160px"></div></td>
                            <td><div class="skel" style="width:90px"></div></td>
                            <td><div class="skel" style="width:70px"></div></td>
                            <td><div class="skel" style="width:50px"></div></td>
                            <td><div class="skel" style="width:50px"></div></td>
                            <td></td>
                        </tr>
                    </template>
                    <tr v-else-if="rows.length === 0">
                        <td colspan="7" class="tbl-empty">Нет товаров</td>
                    </tr>
                    <tr v-else v-for="row in rows" :key="row.id" class="clickable" @click="router.push(`/products/${row.id}`)">
                        <td style="color:#94a3b8;font-size:13px">#{{ row.id }}</td>
                        <td style="font-weight:500">{{ row.name }}</td>
                        <td style="color:#64748b;font-size:13px">{{ row.category || '—' }}</td>
                        <td style="font-weight:500;color:#0f172a">{{ formatPrice(row.price) }}</td>
                        <td>
                            <span :class="['badge', row.stock > 0 ? 'badge-ok' : 'badge-low']">
                                {{ row.stock }}
                            </span>
                        </td>
                        <td>
                            <span :class="['badge', row.active ? 'badge-active' : 'badge-inactive']">
                                {{ row.active ? 'Активен' : 'Скрыт' }}
                            </span>
                        </td>
                        <td>
                            <button class="row-action" @click.stop="router.push(`/products/${row.id}`)">
                                <i class="pi pi-pencil" style="font-size:12px"></i>
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

    <Dialog v-model:visible="showDialog" header="Новый товар" modal style="width:480px">
        <div class="flex flex-col gap-3 mt-2">
            <div class="flex flex-col gap-1">
                <label class="text-sm font-medium">Название *</label>
                <InputText v-model="form.name" placeholder="Название товара" />
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div class="flex flex-col gap-1">
                    <label class="text-sm font-medium">Цена (₽)</label>
                    <InputText v-model.number="form.price" type="number" placeholder="0" />
                </div>
                <div class="flex flex-col gap-1">
                    <label class="text-sm font-medium">Остаток</label>
                    <InputText v-model.number="form.stock" type="number" placeholder="0" />
                </div>
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-sm font-medium">Категория</label>
                <InputText v-model="form.category" placeholder="Категория" />
            </div>
            <div class="flex flex-col gap-1">
                <label class="text-sm font-medium">Описание</label>
                <Textarea v-model="form.description" rows="3" placeholder="Описание товара" class="w-full" />
            </div>
        </div>
        <template #footer>
            <Button label="Отмена" text @click="showDialog = false" />
            <Button label="Создать" :loading="saving" @click="submit" />
        </template>
    </Dialog>
</template>
