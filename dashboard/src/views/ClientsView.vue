<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useClientsStore } from '@/stores/clients.js';

const router = useRouter();
const toast = useToast();
const store = useClientsStore();

const showDialog = ref(false);
const saving = ref(false);
const form = ref({ name: '', phone: '', email: '' });

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
</script>

<template>
    <div class="card">
        <div class="flex justify-between items-center mb-4">
            <div class="font-semibold text-xl">Клиенты</div>
            <Button label="Добавить" icon="pi pi-plus" @click="openCreate" />
        </div>

        <Message v-if="store.error" severity="error" class="mb-3">{{ store.error }}</Message>

        <DataTable
            :value="store.list"
            :loading="store.loading"
            stripedRows
            paginator
            :rows="20"
            dataKey="id"
        >
            <Column field="id" header="ID" sortable style="width: 70px" />
            <Column field="name" header="Имя" sortable />
            <Column field="phone" header="Телефон" />
            <Column field="email" header="Email" />
            <Column field="created_at" header="Создан" sortable>
                <template #body="{ data }">{{ formatDate(data.created_at) }}</template>
            </Column>
            <Column style="width: 60px">
                <template #body="{ data }">
                    <Button icon="pi pi-eye" text rounded size="small" @click="router.push(`/clients/${data.id}`)" />
                </template>
            </Column>
        </DataTable>

        <!-- Диалог создания -->
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
    </div>
</template>
