import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router/index.js';

import Aura from '@primeuix/themes/aura';
import PrimeVue from 'primevue/config';
import ToastService from 'primevue/toastservice';

import './app.css';
import 'primeicons/primeicons.css';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(PrimeVue, {
    theme: {
        preset: Aura,
        options: { darkModeSelector: false },
    },
});
app.use(ToastService);
app.mount('#app');
