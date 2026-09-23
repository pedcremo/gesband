{% load static %}/* Cascaron sin conexion del cliente del musico.
   Los datos nunca se sirven de cache: una convocatoria caducada enganaria. */
const SHELL = "gesband-shell-{{ shell_version }}";
const FILES = [
  "/app/",
  "{% static 'member_app/app.css' %}?v={{ shell_version }}",
  "{% static 'member_app/app.js' %}?v={{ shell_version }}",
  "{% static 'member_app/icon.svg' %}?v={{ shell_version }}",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((name) => name !== SHELL).map((name) => caches.delete(name))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // La API siempre va a la red: los datos de una banda cambian y caducan.
  if (url.pathname.startsWith("/api/")) return;

  event.respondWith(
    caches.match(request).then((hit) =>
      hit || fetch(request).catch(() => caches.match("/app/"))
    )
  );
});
