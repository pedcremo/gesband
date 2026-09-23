/* Cliente web del musico. Habla con /api/v1/ desde el mismo origen.
   Sin framework ni paso de compilacion: es una herramienta de desarrollo. */
(() => {
  "use strict";

  const API = "/api/v1";
  const STORE = { token: "gesband.token", association: "gesband.association", lang: "gesband.lang" };

  const STRINGS = {
    es: {
      appName: "Gesband", agenda: "Agenda", inbox: "Avisos", profile: "Mi ficha",
      email: "Correo electrónico", password: "Contraseña", signIn: "Entrar",
      signingIn: "Entrando…", signOut: "Salir", association: "Asociación",
      badCredentials: "Correo o contraseña incorrectos.",
      noAssociations: "Tu cuenta no pertenece a ninguna asociación activa.",
      noActivities: "No tienes ninguna convocatoria.",
      noNotices: "No tienes avisos.",
      pending: "Pendiente", accepted: "Aceptada", declined: "Rechazada",
      rehearsal: "Ensayo", performance: "Actuación",
      draft: "Borrador", published: "Publicada", cancelled: "Cancelada", completed: "Completada",
      mandatory: "Obligatoria",
      reconfirm: "Ha cambiado la fecha o el lugar: vuelve a confirmar.",
      cancelledNotice: "Esta actividad se ha cancelado.",
      deadlinePassed: "El plazo de respuesta ha terminado.",
      starts: "Inicio", ends: "Final", meeting: "Concentración", place: "Lugar",
      uniform: "Uniforme", deadline: "Plazo de respuesta", programme: "Repertorio",
      description: "Descripción", yourAnswer: "Tu respuesta", note: "Nota",
      accept: "Acepto", decline: "No puedo", change: "Cambiar respuesta",
      reasonLabel: "Motivo de la ausencia",
      reasonRequired: "En una actividad obligatoria hay que indicar el motivo.",
      sending: "Enviando…", back: "Volver", retry: "Reintentar",
      offline: "Sin conexión. Se muestra lo último que se descargó.",
      loadFailed: "No se han podido cargar los datos.",
      instruments: "Instrumentos", phone: "Teléfono", noInstruments: "Sin instrumentos asignados.",
      language: "Idioma",
    },
    ca: {
      appName: "Gesband", agenda: "Agenda", inbox: "Avisos", profile: "La meua fitxa",
      email: "Correu electrònic", password: "Contrasenya", signIn: "Entrar",
      signingIn: "Entrant…", signOut: "Eixir", association: "Associació",
      badCredentials: "Correu o contrasenya incorrectes.",
      noAssociations: "El teu compte no pertany a cap associació activa.",
      noActivities: "No tens cap convocatòria.",
      noNotices: "No tens avisos.",
      pending: "Pendent", accepted: "Acceptada", declined: "Rebutjada",
      rehearsal: "Assaig", performance: "Actuació",
      draft: "Esborrany", published: "Publicada", cancelled: "Cancel·lada", completed: "Completada",
      mandatory: "Obligatòria",
      reconfirm: "Ha canviat la data o el lloc: torna a confirmar.",
      cancelledNotice: "Aquesta activitat s'ha cancel·lat.",
      deadlinePassed: "El termini de resposta ha acabat.",
      starts: "Inici", ends: "Final", meeting: "Concentració", place: "Lloc",
      uniform: "Uniforme", deadline: "Termini de resposta", programme: "Repertori",
      description: "Descripció", yourAnswer: "La teua resposta", note: "Nota",
      accept: "Accepte", decline: "No puc", change: "Canviar resposta",
      reasonLabel: "Motiu de l'absència",
      reasonRequired: "En una activitat obligatòria cal indicar el motiu.",
      sending: "Enviant…", back: "Tornar", retry: "Reintentar",
      offline: "Sense connexió. Es mostra l'últim que es va descarregar.",
      loadFailed: "No s'han pogut carregar les dades.",
      instruments: "Instruments", phone: "Telèfon", noInstruments: "Sense instruments assignats.",
      language: "Idioma",
    },
    en: {
      appName: "Gesband", agenda: "Agenda", inbox: "Notices", profile: "My details",
      email: "Email", password: "Password", signIn: "Sign in",
      signingIn: "Signing in…", signOut: "Sign out", association: "Association",
      badCredentials: "Wrong email or password.",
      noAssociations: "Your account belongs to no active association.",
      noActivities: "You have no invitations.",
      noNotices: "You have no notices.",
      pending: "Pending", accepted: "Accepted", declined: "Declined",
      rehearsal: "Rehearsal", performance: "Performance",
      draft: "Draft", published: "Published", cancelled: "Cancelled", completed: "Completed",
      mandatory: "Mandatory",
      reconfirm: "The date or the place changed: please confirm again.",
      cancelledNotice: "This activity has been cancelled.",
      deadlinePassed: "The response deadline has passed.",
      starts: "Start", ends: "End", meeting: "Meeting", place: "Place",
      uniform: "Uniform", deadline: "Response deadline", programme: "Programme",
      description: "Description", yourAnswer: "Your answer", note: "Note",
      accept: "I can come", decline: "I cannot", change: "Change answer",
      reasonLabel: "Reason for the absence",
      reasonRequired: "A mandatory activity needs a reason.",
      sending: "Sending…", back: "Back", retry: "Retry",
      offline: "Offline. Showing the last downloaded data.",
      loadFailed: "The data could not be loaded.",
      instruments: "Instruments", phone: "Phone", noInstruments: "No instruments assigned.",
      language: "Language",
    },
  };

  const read = (key) => { try { return localStorage.getItem(key); } catch { return null; } };
  const write = (key, value) => {
    try { value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value); } catch { /* modo privado */ }
  };

  const state = {
    token: read(STORE.token),
    lang: STRINGS[read(STORE.lang)] ? read(STORE.lang) : "es",
    account: null,
    associations: [],
    associationId: read(STORE.association),
    tab: "agenda",
    activities: [],
    notifications: [],
    activity: null,
    banner: null,
    busy: false,
  };

  const t = (key) => STRINGS[state.lang][key] ?? key;
  const association = () => state.associations.find((item) => item.id === state.associationId) || state.associations[0];

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function formatDate(value, withTime = true) {
    if (!value) return "—";
    const zone = association()?.timezone || undefined;
    const options = withTime
      ? { dateStyle: "full", timeStyle: "short", timeZone: zone }
      : { dateStyle: "full", timeZone: zone };
    try { return new Intl.DateTimeFormat(state.lang, options).format(new Date(value)); }
    catch { return new Date(value).toLocaleString(); }
  }

  async function api(path, { method = "GET", body, association: scoped = true } = {}) {
    const headers = { "Accept-Language": state.lang };
    if (state.token) headers.Authorization = `Token ${state.token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (scoped && state.associationId) headers["X-Association-ID"] = state.associationId;

    const separator = path.includes("?") ? "&" : "?";
    const url = scoped && state.associationId ? `${API}${path}${separator}association_id=${state.associationId}` : `${API}${path}`;
    const response = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });

    if (response.status === 401) { signOut({ silent: true }); throw new Error("unauthorized"); }
    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;
    if (!response.ok) {
      const error = new Error("api");
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  const problem = (error) => {
    const payload = error?.payload;
    if (!payload) return t("loadFailed");
    if (typeof payload.detail === "string") return payload.detail;
    const first = Object.values(payload)[0];
    return Array.isArray(first) ? String(first[0]) : String(first ?? t("loadFailed"));
  };

  /* --- vistas --- */

  function viewLogin() {
    return `
      <header class="bar"><h1>${esc(t("appName"))}</h1>${languageSelect()}</header>
      <main>
        ${state.banner ? banner() : ""}
        <form class="stack" data-form="login">
          <div>
            <label for="email">${esc(t("email"))}</label>
            <input id="email" name="email" type="email" autocomplete="username" required autocapitalize="none" spellcheck="false">
          </div>
          <div>
            <label for="password">${esc(t("password"))}</label>
            <input id="password" name="password" type="password" autocomplete="current-password" required>
          </div>
          <button class="button" type="submit"${state.busy ? " disabled" : ""}>
            ${esc(state.busy ? t("signingIn") : t("signIn"))}
          </button>
        </form>
      </main>`;
  }

  const languageSelect = () => `
    <select data-action="language" aria-label="${esc(t("language"))}">
      ${["es", "ca", "en"].map((code) =>
        `<option value="${code}"${code === state.lang ? " selected" : ""}>${{ es: "Castellano", ca: "Valencià", en: "English" }[code]}</option>`
      ).join("")}
    </select>`;

  const banner = () => `<p class="notice${state.banner.kind === "error" ? " error" : ""}">${esc(state.banner.text)}</p>`;

  function shell(content) {
    const unread = state.notifications.filter((item) => !item.read_at).length;
    const picker = state.associations.length > 1
      ? `<select data-action="association" aria-label="${esc(t("association"))}">
           ${state.associations.map((item) =>
             `<option value="${esc(item.id)}"${item.id === state.associationId ? " selected" : ""}>${esc(item.name)}</option>`
           ).join("")}
         </select>`
      : "";
    return `
      <header class="bar">
        <h1>${esc(association()?.name || t("appName"))}</h1>
        ${picker}${languageSelect()}
        <button data-action="signout">${esc(t("signOut"))}</button>
        <span class="who">${esc(state.account?.display_name || "")}</span>
      </header>
      <nav class="tabs">
        <button data-tab="agenda"${state.tab === "agenda" ? ' aria-current="page"' : ""}>${esc(t("agenda"))}</button>
        <button data-tab="inbox"${state.tab === "inbox" ? ' aria-current="page"' : ""}>${esc(t("inbox"))}${unread ? `<span class="badge">${unread}</span>` : ""}</button>
        <button data-tab="profile"${state.tab === "profile" ? ' aria-current="page"' : ""}>${esc(t("profile"))}</button>
      </nav>
      <main>${state.banner ? banner() : ""}${content}</main>`;
  }

  function viewAgenda() {
    if (!state.activities.length) return shell(`<p class="empty">${esc(t("noActivities"))}</p>`);
    const cards = state.activities.map((activity) => {
      const mine = activity.invitations?.[0];
      const chips = [
        `<span class="chip ${esc(mine?.response || "pending")}">${esc(t(mine?.response || "pending"))}</span>`,
        activity.status === "cancelled" ? `<span class="chip cancelled">${esc(t("cancelled"))}</span>` : "",
        activity.is_mandatory ? `<span class="chip mandatory">${esc(t("mandatory"))}</span>` : "",
      ].join(" ");
      return `
        <button class="card" data-activity="${esc(activity.id)}">
          <h3>${esc(activity.title)}</h3>
          <p class="when">${esc(t(activity.kind))} · ${esc(formatDate(activity.starts_at))}</p>
          <p>${chips}</p>
          ${mine?.needs_reconfirmation ? `<p class="notice">${esc(t("reconfirm"))}</p>` : ""}
        </button>`;
    });
    return shell(cards.join(""));
  }

  function viewActivity() {
    const activity = state.activity;
    const mine = activity.invitations?.[0];
    const deadlinePassed = activity.response_deadline && new Date(activity.response_deadline) < new Date();
    const closed = activity.status !== "published" || deadlinePassed;

    const facts = [
      [t("starts"), formatDate(activity.starts_at)],
      activity.ends_at ? [t("ends"), formatDate(activity.ends_at)] : null,
      activity.meeting_at ? [t("meeting"), formatDate(activity.meeting_at)] : null,
      activity.location ? [t("place"), activity.location] : null,
      activity.uniform ? [t("uniform"), activity.uniform] : null,
      activity.response_deadline ? [t("deadline"), formatDate(activity.response_deadline)] : null,
      activity.description ? [t("description"), activity.description] : null,
    ].filter(Boolean);

    const programme = activity.programme?.length
      ? `<h3>${esc(t("programme"))}</h3><ol>${activity.programme.map((item) =>
          `<li>${esc(item.title)}${item.notes ? ` <span class="muted">— ${esc(item.notes)}</span>` : ""}</li>`).join("")}</ol>`
      : "";

    const answer = mine
      ? `<h3>${esc(t("yourAnswer"))}: <span class="chip ${esc(mine.response)}">${esc(t(mine.response))}</span></h3>
         ${mine.response_note ? `<p class="muted">${esc(t("note"))}: ${esc(mine.response_note)}</p>` : ""}
         ${closed ? "" : `
           <form class="stack" data-form="respond" data-invitation="${esc(mine.id)}">
             ${activity.is_mandatory ? `
               <div>
                 <label for="note">${esc(t("reasonLabel"))}</label>
                 <textarea id="note" name="note" rows="2" maxlength="500"></textarea>
               </div>` : ""}
             <div class="actions">
               <button class="button" type="submit" name="response" value="accepted"${state.busy ? " disabled" : ""}>${esc(t("accept"))}</button>
               <button class="button danger" type="submit" name="response" value="declined"${state.busy ? " disabled" : ""}>${esc(t("decline"))}</button>
             </div>
           </form>`}`
      : "";

    return shell(`
      <button class="back" data-action="agenda">← ${esc(t("back"))}</button>
      <h2>${esc(activity.title)}</h2>
      <p>
        <span class="chip">${esc(t(activity.kind))}</span>
        ${activity.is_mandatory ? `<span class="chip mandatory">${esc(t("mandatory"))}</span>` : ""}
      </p>
      ${activity.status === "cancelled" ? `<p class="notice error">${esc(t("cancelledNotice"))}</p>` : ""}
      ${mine?.needs_reconfirmation ? `<p class="notice">${esc(t("reconfirm"))}</p>` : ""}
      ${deadlinePassed && activity.status === "published" ? `<p class="notice">${esc(t("deadlinePassed"))}</p>` : ""}
      <dl class="facts">${facts.map(([term, value]) => `<dt>${esc(term)}</dt><dd>${esc(value)}</dd>`).join("")}</dl>
      ${programme}
      ${answer}`);
  }

  function viewInbox() {
    if (!state.notifications.length) return shell(`<p class="empty">${esc(t("noNotices"))}</p>`);
    return shell(state.notifications.map((notice) => `
      <button class="card${notice.read_at ? "" : " unread"}" data-notification="${esc(notice.id)}">
        <h3>${esc(notice.title)}</h3>
        <p class="when">${esc(formatDate(notice.created_at))}</p>
        <p>${esc(notice.body).replace(/\n/g, "<br>")}</p>
      </button>`).join(""));
  }

  function viewProfile() {
    const member = state.member;
    if (!member) return shell(`<p class="empty">${esc(t("loadFailed"))}</p>`);
    const instruments = member.instruments?.length
      ? member.instruments.map((item) => esc(item.name || item)).join(", ")
      : t("noInstruments");
    return shell(`
      <h2>${esc(`${member.first_name} ${member.last_name}`.trim())}</h2>
      <dl class="facts">
        <dt>${esc(t("email"))}</dt><dd>${esc(member.email || "—")}</dd>
        <dt>${esc(t("phone"))}</dt><dd>${esc(member.phone || "—")}</dd>
        <dt>${esc(t("instruments"))}</dt><dd>${instruments}</dd>
      </dl>`);
  }

  /* --- datos --- */

  async function loadSession() {
    const me = await api("/auth/me", { association: false });
    state.account = me.account;
    state.associations = me.associations || [];
    if (!state.associations.length) {
      state.banner = { kind: "error", text: t("noAssociations") };
      return;
    }
    if (!state.associations.some((item) => item.id === state.associationId)) {
      state.associationId = state.associations[0].id;
      write(STORE.association, state.associationId);
    }
  }

  async function loadTab() {
    try {
      if (state.tab === "agenda") {
        const page = await api("/activities/");
        state.activities = page.results || page;
      } else if (state.tab === "inbox") {
        const page = await api("/notifications/", { association: false });
        state.notifications = page.results || page;
      } else if (state.tab === "profile") {
        state.member = await api("/members/me/");
      }
      state.banner = null;
    } catch (error) {
      if (error.message === "unauthorized") return;
      state.banner = { kind: "error", text: navigator.onLine ? problem(error) : t("offline") };
    }
  }

  function signOut({ silent = false } = {}) {
    state.token = null; state.account = null; state.activities = []; state.notifications = [];
    state.activity = null; state.member = null;
    write(STORE.token, null);
    if (!silent) state.banner = null;
    render();
  }

  /* --- render y eventos --- */

  const root = document.getElementById("app");

  function render() {
    if (!state.token) { root.innerHTML = viewLogin(); return; }
    if (state.activity) { root.innerHTML = viewActivity(); return; }
    root.innerHTML = { agenda: viewAgenda, inbox: viewInbox, profile: viewProfile }[state.tab]();
  }

  root.addEventListener("click", async (event) => {
    const target = event.target.closest("[data-tab], [data-activity], [data-notification], [data-action]");
    if (!target) return;

    if (target.dataset.tab) {
      state.tab = target.dataset.tab; state.activity = null;
      render(); await loadTab(); render(); return;
    }
    if (target.dataset.activity) {
      state.activity = state.activities.find((item) => item.id === target.dataset.activity);
      render(); return;
    }
    if (target.dataset.notification) {
      const id = target.dataset.notification;
      try {
        const fresh = await api(`/notifications/${id}/`, { association: false });
        state.notifications = state.notifications.map((item) => (item.id === fresh.id ? fresh : item));
        render();
      } catch { /* leerlo no es critico */ }
      return;
    }
    if (target.dataset.action === "signout") { signOut(); return; }
    if (target.dataset.action === "agenda") { state.activity = null; render(); return; }
  });

  root.addEventListener("change", async (event) => {
    const select = event.target.closest("select[data-action]");
    if (!select) return;
    if (select.dataset.action === "language") {
      state.lang = select.value; write(STORE.lang, state.lang);
      document.documentElement.lang = state.lang;
      render(); await loadTab(); render(); return;
    }
    if (select.dataset.action === "association") {
      state.associationId = select.value; write(STORE.association, state.associationId);
      state.activity = null;
      render(); await loadTab(); render();
    }
  });

  root.addEventListener("submit", async (event) => {
    const form = event.target;
    event.preventDefault();
    if (state.busy) return;

    if (form.dataset.form === "login") {
      const data = new FormData(form);
      state.busy = true; state.banner = null; render();
      try {
        const session = await api("/auth/login", {
          method: "POST",
          association: false,
          body: { email: data.get("email"), password: data.get("password") },
        });
        state.token = session.access_token;
        write(STORE.token, state.token);
        await loadSession();
        state.busy = false;
        render(); await loadTab(); render();
      } catch (error) {
        state.busy = false;
        state.banner = { kind: "error", text: error.status === 400 || error.status === 401 ? t("badCredentials") : problem(error) };
        render();
      }
      return;
    }

    if (form.dataset.form === "respond") {
      const response = event.submitter?.value;
      const note = (form.elements.note?.value || "").trim();
      if (state.activity.is_mandatory && response === "declined" && !note) {
        state.banner = { kind: "error", text: t("reasonRequired") };
        render(); return;
      }
      state.busy = true; state.banner = null; render();
      try {
        await api(`/activities/${state.activity.id}/respond/`, {
          method: "POST",
          body: { invitation_id: form.dataset.invitation, response, note },
        });
        state.busy = false;
        const id = state.activity.id;
        await loadTab();
        state.activity = state.activities.find((item) => item.id === id) || null;
        render();
      } catch (error) {
        state.busy = false;
        state.banner = { kind: "error", text: problem(error) };
        render();
      }
    }
  });

  window.addEventListener("online", () => { state.banner = null; render(); });

  document.documentElement.lang = state.lang;
  render();
  if (state.token) {
    loadSession()
      .then(() => { render(); return loadTab(); })
      .then(render)
      .catch(() => render());
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/app/sw.js").catch(() => {}));
  }
})();
