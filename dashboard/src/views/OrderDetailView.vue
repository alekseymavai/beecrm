<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useOrdersStore, STATUS_SEVERITY, SOURCE_LABEL } from '@/stores/orders.js';

const props = defineProps({ id: String });
const router = useRouter();
const toast = useToast();
const store = useOrdersStore();
const saving = ref(false);

onMounted(async () => {
    await store.fetchOne(props.id);
    await store.fetchHistory(props.id);
});

const transitions = computed(() => (store.current ? store.availableTransitions(store.current.status) : []));

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

async function changeStatus(status) {
    saving.value = true;
    try {
        await store.updateStatus(props.id, status);
        await store.fetchHistory(props.id);
        toast.add({ severity: 'success', summary: 'Статус изменён', detail: `→ ${status}`, life: 3000 });
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
            <span class="font-semibold text-xl">Заказ #{{ id }}</span>
            <Tag v-if="store.current" :value="store.current.status" :severity="STATUS_SEVERITY[store.current.status]" />
        </div>

        <Message v-if="store.error" severity="error" class="mb-3">{{ store.error }}</Message>

        <div v-if="store.current" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Детали -->
            <div class="card">
                <div class="font-semibold mb-3">Детали</div>
                <div class="flex flex-col gap-2 text-sm">
                    <div><span class="text-muted-color">Клиент ID:</span> <RouterLink :to="`/clients/${store.current.client_id}`" class="text-primary">{{ store.current.client_id }}</RouterLink></div>
                    <div><span class="text-muted-color">Источник:</span> {{ SOURCE_LABEL[store.current.source] ?? store.current.source }}</div>
                    <div><span class="text-muted-color">Создан:</span> {{ formatDate(store.current.created_at) }}</div>
                    <div><span class="text-muted-color">Обновлён:</span> {{ formatDate(store.current.updated_at) }}</div>
                </div>

                <!-- Смена статуса -->
                <div v-if="transitions.length" class="flex gap-2 mt-4 flex-wrap">
                    <Button
                        v-for="t in transitions"
                        :key="t"
                        :label="t"
                        :severity="STATUS_SEVERITY[t]"
                        size="small"
                        :loading="saving"
                        @click="changeStatus(t)"
                    />
                </div>
                <div v-else class="mt-4 text-sm text-muted-color italic">Финальный статус, переходов нет</div>
            </div>

            <!-- Payload -->
            <div class="card">
                <div class="font-semibold mb-3">Данные заказа</div>
                <pre class="text-xs bg-surface-100 dark:bg-surface-800 p-3 rounded-lg overflow-auto max-h-60">{{ JSON.stringify(store.current.payload, null, 2) }}</pre>
            </div>
        </div>

        <!-- История -->
        <div class="card mt-4">
            <div class="font-semibold mb-3">История статусов</div>
            <DataTable :value="store.history" stripedRows :rows="10" size="small">
                <Column field="from_status" header="Было">
                    <template #body="{ data }">
                        <Tag v-if="data.from_status" :value="data.from_status" :severity="STATUS_SEVERITY[data.from_status]" />
                        <span v-else class="text-muted-color">—</span>
                    </template>
                </Column>
                <Column field="to_status" header="Стало">
                    <template #body="{ data }">
                        <Tag :value="data.to_status" :severity="STATUS_SEVERITY[data.to_status]" />
                    </template>
                </Column>
                <Column field="actor" header="Кто" />
                <Column field="created_at" header="Когда">
                    <template #body="{ data }">{{ formatDate(data.created_at) }}</template>
                </Column>
            </DataTable>
        </div>
    </div>
</template>
