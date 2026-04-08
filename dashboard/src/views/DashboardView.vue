<script setup>
import { onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useOrdersStore, SOURCE_LABEL } from '@/stores/orders.js';
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

const STATUS_LABEL = { NEW: 'Новый', CONFIRMED: 'Подтверждён', IN_PROGRESS: 'В работе', DONE: 'Выполнен', CANCELLED: 'Отменён' };
const STATUS_CLASS = { NEW: 'badge-new', CONFIRMED: 'badge-confirmed', IN_PROGRESS: 'badge-in_progress', DONE: 'badge-done', CANCELLED: 'badge-cancelled' };

const todayOrders = computed(() => {
    const today = new Date().toISOString().slice(0, 10);
    return orders.list.filter(o => (o.created_at || '').startsWith(today));
});

const activeProducts = computed(() => products.list.filter(p => p.active).length);
const revenue = computed(() => orders.list.reduce((sum, o) => sum + (Number(o.amount) || 0), 0));
const recentOrders = computed(() => [...orders.list].slice(0, 5));
</script>

<template>
    <div>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-card__icon"><i class="pi pi-shopping-cart"></i></div>
                <div class="stat-card__value">{{ todayOrders.length }}</div>
                <div class="stat-card__label">Заказов сегодня</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__icon"><i class="pi pi-users"></i></div>
                <div class="stat-card__value">{{ clients.list.length }}</div>
                <div class="stat-card__label">Клиентов</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__icon"><i class="pi pi-tag"></i></div>
                <div class="stat-card__value">{{ activeProducts }}</div>
                <div class="stat-card__label">Товаров активных</div>
            </div>
            <div class="stat-card">
                <div class="stat-card__icon"><i class="pi pi-wallet"></i></div>
                <div class="stat-card__value">{{ revenue.toLocaleString('ru-RU') }} ₽</div>
                <div class="stat-card__label">Общая выручка</div>
            </div>
        </div>

        <div class="card">
            <div class="page-header">
                <span class="page-title">Последние заказы</span>
                <button class="btn-link" @click="router.push('/orders')">Все заказы →</button>
            </div>

            <div class="tbl-wrap">
                <table class="tbl">
                    <thead>
                        <tr>
                            <th style="width:70px">ID</th>
                            <th style="width:130px">Источник</th>
                            <th style="width:160px">Статус</th>
                            <th>Дата</th>
                            <th style="width:44px"></th>
                        </tr>
                    </thead>
                    <tbody>
                        <template v-if="orders.loading">
                            <tr v-for="i in 5" :key="i">
                                <td><div class="skel" style="width:36px"></div></td>
                                <td><div class="skel" style="width:80px"></div></td>
                                <td><div class="skel" style="width:90px"></div></td>
                                <td><div class="skel" style="width:80px"></div></td>
                                <td></td>
                            </tr>
                        </template>
                        <tr v-else-if="recentOrders.length === 0">
                            <td colspan="5" class="tbl-empty">Нет заказов</td>
                        </tr>
                        <tr v-else v-for="row in recentOrders" :key="row.id" class="clickable" @click="router.push(`/orders/${row.id}`)">
                            <td style="color:#94a3b8;font-size:13px">#{{ row.id }}</td>
                            <td style="font-size:13px">{{ SOURCE_LABEL[row.source] ?? row.source ?? '—' }}</td>
                            <td>
                                <span :class="['badge', STATUS_CLASS[row.status] ?? 'badge-inactive']">
                                    {{ STATUS_LABEL[row.status] ?? row.status }}
                                </span>
                            </td>
                            <td style="color:#94a3b8;font-size:13px">{{ formatDate(row.created_at) }}</td>
                            <td>
                                <button class="row-action" @click.stop="router.push(`/orders/${row.id}`)">
                                    <i class="pi pi-arrow-right" style="font-size:12px"></i>
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</template>
