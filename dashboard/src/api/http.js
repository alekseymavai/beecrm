import axios from 'axios';

const http = axios.create({
    baseURL: '/api',
    headers: { 'Cache-Control': 'no-store' },
});

http.interceptors.request.use((config) => {
    const key = localStorage.getItem('beecrm_api_key') || import.meta.env.VITE_API_KEY || '';
    config.headers['X-API-Key'] = key;
    return config;
});

export default http;
