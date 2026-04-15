import axios from 'axios';

const http = axios.create({
    baseURL: '/api',
    headers: { 'Cache-Control': 'no-store' },
});

http.interceptors.request.use((config) => {
    const token = localStorage.getItem('beecrm_jwt') || '';
    if (token) config.headers['Authorization'] = `Bearer ${token}`;
    return config;
});

export default http;
