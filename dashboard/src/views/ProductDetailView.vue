<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useProductsStore } from '@/stores/products.js';

const props = defineProps({ id: String });
const router = useRouter();
const toast = useToast();
const store = useProductsStore();
const saving = ref(false);
const form = ref({ name: '', price: 0, category: '', stock: 0, active: true, description: '' });

onMounted(async () => {
    await store.fetchOne(props.id);
    if (store.current) {
        const p = store.current;
        form.value = { name: p.name, price: p.price, category: p.category, stock: p.stock, active: p.active, description: p.description };
    }
});

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
            <span class="font-semibold text-xl">Товар #{{ id }}</span>
            <Tag v-if="store.current" :value="store.current.active ? 'Активен' : 'Неактивен'" :severity="store.current.active ? 'success' : 'secondary'" />
        </div>

        <Message v-if="store.error" severity="error" class="mb-3">{{ store.error }}</Message>

        <div v-if="store.current" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="card">
                <div class="font-semibold mb-3">Данные товара</div>
                <div class="flex flex-col gap-3">
                    <div class="flex flex-col gap-1">
                        <label class="text-sm font-medium">Название</label>
                        <InputText v-model="form.name" />
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div class="flex flex-col gap-1">
                            <label class="text-sm font-medium">Цена (₽)</label>
                            <InputText v-model.number="form.price" type="number" />
                        </div>
                        <div class="flex flex-col gap-1">
                            <label class="text-sm font-medium">Остаток</label>
                            <InputText v-model.number="form.stock" type="number" />
                        </div>
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm font-medium">Категория</label>
                        <InputText v-model="form.category" />
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-sm font-medium">Описание</label>
                        <Textarea v-model="form.description" rows="4" class="w-full" />
                    </div>
                    <div class="flex items-center gap-2">
                        <Checkbox v-model="form.active" :binary="true" inputId="active" />
                        <label for="active" class="text-sm">Активен</label>
                    </div>
                    <Button label="Сохранить" :loading="saving" @click="save" class="mt-1" />
                </div>
            </div>
            <div class="card">
                <div class="font-semibold mb-3">Информация</div>
                <div class="flex flex-col gap-2 text-sm">
                    <div><span class="text-muted-color">ID:</span> {{ store.current.id }}</div>
                    <div><span class="text-muted-color">Создан:</span> {{ new Date(store.current.created_at).toLocaleString('ru-RU') }}</div>
                    <div><span class="text-muted-color">Цена:</span> {{ Number(store.current.price).toLocaleString('ru-RU') }} ₽</div>
                    <div><span class="text-muted-color">Остаток:</span> {{ store.current.stock }} шт.</div>
                </div>
            </div>
        </div>
    </div>
</template>
