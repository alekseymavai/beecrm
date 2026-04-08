<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useOrdersStore, STATUS_SEVERITY, SOURCE_LABEL } from '@/stores/orders.js';

const router = useRouter();
const toast = useToast();
const store = useOrdersStore();

const importLoading = ref(false);
const importResult = ref(null);

onMounted(() => store.fetchAll());

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

async function onImport(event) {
    const file = event.files?.[0];
    if (!file) return;
    importLoading.value = true;
    importResult.value = null;
    try {
        const result = await store.importExcel(file);
        importResult.value = result;
        toast.add({ severity: 'success', summary: 'Импорт завершён', detail: `Создано: ${result.created}, ошибок: ${result.errors?.length ?? 0}`, life: 4000 });
        await store.fetchAll();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Ошибка импорта', detail: e.response?.data?.detail || e.message, life: 5000 });
    } finally {
        importLoading.value = false;
    }
}
</script>

<template>
    <div class="card">
        <div class="flex justify-between items-center mb-4">
            <div class="font-semibold text-xl">Заказы</div>
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

        <DataTable
            :value="store.list"
            :loading="store.loading"
            stripedRows
            paginator
            :rows="20"
            dataKey="id"
            :globalFilterFields="['id', 'source', 'status', 'client_id']"
        >
            <Column field="id" header="ID" sortable style="width: 70px" />
            <Column field="client_id" header="Клиент ID" sortable style="width: 110px" />
            <Column field="source" header="Источник" sortable style="width: 130px">
                <template #body="{ data }">
                    {{ SOURCE_LABEL[data.source] ?? data.source }}
                </template>
            </Column>
            <Column field="status" header="Статус" sortable style="width: 150px">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="STATUS_SEVERITY[data.status]" />
                </template>
            </Column>
            <Column field="created_at" header="Создан" sortable>
                <template #body="{ data }">{{ formatDate(data.created_at) }}</template>
            </Column>
            <Column style="width: 60px">
                <template #body="{ data }">
                    <Button icon="pi pi-eye" text rounded size="small" @click="router.push(`/orders/${data.id}`)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>
