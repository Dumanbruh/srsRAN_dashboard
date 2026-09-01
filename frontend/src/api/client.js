function getCookie(name) {
  return document.cookie
    .split(';')
    .map((c) => c.trim())
    .find((c) => c.startsWith(name + '='))
    ?.split('=')[1] || '';
}

// login_required redirects an expired session to /login/ (302). fetch()
// follows that transparently, so a plain .json() call would try to parse
// the login page's HTML. Detect the redirect and bounce to /login/ instead.
function assertNotRedirectedToLogin(res) {
  if (res.redirected && res.url.includes('/login/')) {
    window.location.href = '/login/';
    throw new Error('session expired');
  }
}

export async function apiGet(url) {
  const res = await fetch(url, { credentials: 'same-origin' });
  assertNotRedirectedToLogin(res);
  return res.json();
}

export async function apiPost(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
    body: JSON.stringify(data || {}),
  });
  assertNotRedirectedToLogin(res);
  return res.json();
}

export { getCookie };
