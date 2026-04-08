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

onMounted(() => store.fetchAll());

const filtered = computed(() => {
    if (!search.value) return store.list;
    const q = search.value.toLowerCase();
    return store.list.filter(p => p.name.toLowerCase().includes(q) || p.category.toLowerCase().includes(q));
});

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

function formatPrice(v) {
    return Number(v).toLocaleString('ru-RU') + ' ₽';
}
</script>

<template>
    <div class="card">
        <div class="page-header">
            <span class="page-title">Товары</span>
            <div class="flex gap-2">
                <InputText v-model="search" placeholder="Поиск..." size="small" />
                <Button label="+ Добавить" @click="openCreate" />
            </div>
        </div>

        <Message v-if="store.error" severity="error" class="mb-3">{{ store.error }}</Message>

        <DataTable :value="filtered" :loading="store.loading" stripedRows paginator :rows="20" dataKey="id">
            <Column field="id" header="ID" style="width:60px" sortable />
            <Column field="name" header="Название" sortable />
            <Column field="category" header="Категория" />
            <Column field="price" header="Цена" sortable>
                <template #body="{ data }">{{ formatPrice(data.price) }}</template>
            </Column>
            <Column field="stock" header="Остаток" sortable>
                <template #body="{ data }">
                    <Tag :value="String(data.stock)" :severity="data.stock > 0 ? 'success' : 'danger'" />
                </template>
            </Column>
            <Column field="active" header="Активен">
                <template #body="{ data }">
                    <Tag :value="data.active ? 'Да' : 'Нет'" :severity="data.active ? 'success' : 'secondary'" />
                </template>
            </Column>
            <Column style="width:60px">
                <template #body="{ data }">
                    <Button icon="pi pi-pencil" text rounded size="small" @click="router.push(`/products/${data.id}`)" />
                </template>
            </Column>
        </DataTable>

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
    </div>
</template>
