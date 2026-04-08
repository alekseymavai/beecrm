import axios from 'axios';

const http = axios.create({
    baseURL: '/api',
    headers: {
        'X-API-Key': import.meta.env.VITE_API_KEY || '',
        'Cache-Control': 'no-store'
    }
});

export default http;
