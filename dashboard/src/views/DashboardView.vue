<script setup>
import { onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useOrdersStore, STATUS_SEVERITY, SOURCE_LABEL } from '@/stores/orders.js';
import { useClientsStore } from '@/stores/clients.js';
import { useProductsStore } from '@/stores/products.js';

const router = useRouter();
const orders = useOrdersStore();
const clients = useClientsStore();
const products = useProductsStore();

onMounted(() => {
    Promise.all([orders.fetchAll(), clients.fetchAll(), products.fetchAll()]);
});

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

const todayOrders = computed(() => {
    const today = new Date().toISOString().slice(0, 10);
    return orders.list.filter(o => (o.created_at || '').startsWith(today));
});

const activeProducts = computed(() => products.list.filter(p => p.active).length);

const revenue = computed(() =>
    orders.list.reduce((sum, o) => sum + (Number(o.amount) || 0), 0)
);

const recentOrders = computed(() => [...orders.list].slice(0, 5));
</script>

<template>
    <div>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-card__value">{{ todayOrders.length }}</div>
                <div class="stat-card__label">Заказов сегодня</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__value">{{ clients.list.length }}</div>
                <div class="stat-card__label">Клиентов</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__value">{{ activeProducts }}</div>
                <div class="stat-card__label">Товаров активных</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__value">{{ revenue.toLocaleString('ru-RU') }} ₽</div>
                <div class="stat-card__label">Общая выручка</div>
            </div>
        </div>

        <div class="card">
            <div class="page-header">
                <span class="page-title">Последние заказы</span>
                <Button label="Все заказы" text size="small" @click="router.push('/orders')" />
            </div>
            <DataTable :value="recentOrders" :loading="orders.loading" size="small">
                <Column field="id" header="ID" style="width:60px" />
                <Column field="source" header="Источник">
                    <template #body="{ data }">{{ SOURCE_LABEL[data.source] ?? data.source }}</template>
                </Column>
                <Column field="status" header="Статус">
                    <template #body="{ data }">
                        <Tag :value="data.status" :severity="STATUS_SEVERITY[data.status]" />
                    </template>
                </Column>
                <Column field="created_at" header="Дата">
                    <template #body="{ data }">{{ formatDate(data.created_at) }}</template>
                </Column>
                <Column style="width:50px">
                    <template #body="{ data }">
                        <Button icon="pi pi-eye" text rounded size="small" @click="router.push(`/orders/${data.id}`)" />
                    </template>
                </Column>
            </DataTable>
        </div>
    </div>
</template>
