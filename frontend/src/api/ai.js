import { apiPost, getCookie } from './client';

export const aiChat = (message, history) => apiPost('/api/ai/chat/', { message, history });

// Reachability probe only — status code matters (502 = Ollama down), body is
// ignored (a 503 "no UE data" still means Ollama itself is reachable).
export async function probeOllamaStatus() {
  const res = await fetch('/api/ai/insight/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
    body: '{}',
  });
  return res.status;
}
