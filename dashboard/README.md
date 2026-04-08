# BEECRM Dashboard

Vue 3 дашборд для управления заказами и клиентами.

## Стек

- Vue 3 + Composition API (JS)
- PrimeVue 4 + тема Aura
- Pinia, Vue Router 4, Axios, Vite 5
- Tailwind CSS v4 + tailwindcss-primeui
- Базовый layout: Sakai Vue (primefaces/sakai-vue)
- UX-референс: judas-priest/integram (Notion-стиль)

## Быстрый старт

```bash
cd dashboard
npm install
echo "VITE_API_KEY=your_key" > .env
npm run dev
```

Открыть: http://localhost:5173

## Структура

```
src/
├── api/http.js              # axios + X-API-Key
├── stores/clients.js        # Pinia: клиенты
├── stores/orders.js         # Pinia: заказы + FSM transitions
├── views/beecrm/
│   ├── OrdersView.vue       # /orders — таблица + импорт Excel
│   ├── OrderDetailView.vue  # /orders/:id — карточка + FSM + история
│   ├── ClientsView.vue      # /clients — таблица + создание
│   └── ClientDetailView.vue # /clients/:id — форма + история заказов
├── layout/                  # Sakai layout (sidebar, topbar, menu)
└── router/index.js
```

## Маршруты

| Путь | Страница |
|---|---|
| / | → /orders |
| /orders | Список заказов |
| /orders/:id | Карточка + FSM + история |
| /clients | Список клиентов |
| /clients/:id | Карточка + редактирование |

## FSM переходы

NEW → CONFIRMED → IN_PROGRESS → DONE/CANCELLED

## Proxy (dev)

Все запросы /api/* → http://localhost:8000 (CORS не нужен).
