import { apiGet, getCookie } from './client';

export function primeCsrf() {
  return apiGet('/api/csrf/');
}

export function whoami() {
  return apiGet('/api/whoami/');
}

export async function loginJson(username, password) {
  const res = await fetch('/login/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
    body: JSON.stringify({ username, password }),
  });
  return res.json();
}
