<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useClientsStore } from '@/stores/clients.js';
import { STATUS_SEVERITY, SOURCE_LABEL } from '@/stores/orders.js';

const props = defineProps({ id: String });
const router = useRouter();
const toast = useToast();
const store = useClientsStore();
const saving = ref(false);
const form = ref({ name: '', phone: '', email: '' });

onMounted(async () => {
    await store.fetchOne(props.id);
    await store.fetchHistory(props.id);
    if (store.current) {
        form.value = { name: store.current.name || '', phone: store.current.phone || '', email: store.current.email || '' };
    }
});

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

async function save() {
    saving.value = true;
    try {
        await store.update(props.id, form.value);
        toast.add({ severity: 'success', summary: 'Сохранено', life: 2000 });
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Ошибка', detail: e.response?.data?.detail || e.message, life: 5000 });
    } finally {
        saving.value = false;
    }
}
</script>

<template>
    <div>
        <div class="flex items-center gap-3 mb-4">
            <Button icon="pi pi-arrow-left" text rounded @click="router.back()" />
            <span class="font-semibold text-xl">Клиент #{{ id }}</span>
        </div>

        <Message v-if="store.error" severity="error" class="mb-3">{{ store.error }}</Message>

        <div v-if="store.current" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Форма -->
            <div class="card">
                <div class="font-semibold mb-3">Данные клиента</div>
                <div class="flex flex-col gap-3">
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
                    <Button label="Сохранить" :loading="saving" @click="save" class="mt-1" />
                </div>
            </div>

            <!-- Мета -->
            <div class="card">
                <div class="font-semibold mb-3">Информация</div>
                <div class="flex flex-col gap-2 text-sm">
                    <div><span class="text-muted-color">ID:</span> {{ store.current.id }}</div>
                    <div><span class="text-muted-color">Создан:</span> {{ formatDate(store.current.created_at) }}</div>
                    <div><span class="text-muted-color">Заказов:</span> {{ store.history.length }}</div>
                </div>
            </div>
        </div>

        <!-- История заказов -->
        <div class="card mt-4">
            <div class="font-semibold mb-3">История заказов</div>
            <DataTable :value="store.history" stripedRows :rows="10" size="small">
                <Column field="id" header="ID" style="width: 70px" />
                <Column field="source" header="Источник">
                    <template #body="{ data }">{{ SOURCE_LABEL[data.source] ?? data.source }}</template>
                </Column>
                <Column field="status" header="Статус">
                    <template #body="{ data }">
                        <Tag :value="data.status" :severity="STATUS_SEVERITY[data.status]" />
                    </template>
                </Column>
                <Column field="created_at" header="Создан">
                    <template #body="{ data }">{{ formatDate(data.created_at) }}</template>
                </Column>
                <Column style="width: 60px">
                    <template #body="{ data }">
                        <Button icon="pi pi-eye" text rounded size="small" @click="router.push(`/orders/${data.id}`)" />
                    </template>
                </Column>
            </DataTable>
        </div>
    </div>
</template>
