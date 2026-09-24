/* Cliente web del musico. Habla con /api/v1/ desde el mismo origen.
   Sin framework ni paso de compilacion: es una herramienta de desarrollo.

   La identidad visual la pone cada asociacion (`primary_color`, `secondary_color`,
   `logo_url`, `motto`). Ver `aplicarMarca`: el color elegido nunca se usa tal cual
   para texto, sino corregido hasta que contrasta lo suficiente con el fondo, que es
   el limite de legibilidad que pide ANALISIS.md 2.2. */
(() => {
  "use strict";

  const API = "/api/v1";
  const STORE = {
    token: "gesband.token",
    association: "gesband.association",
    lang: "gesband.lang",
    branding: "gesband.branding",
  };

  const DEFAULT_BRAND = { primary_color: "#1B4965", secondary_color: "#CAE9FF" };

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
      language: "Idioma", settings: "Ajustes", today: "Hoy", tomorrow: "Mañana",
      greeting: "Hola, {name}",
      polls: "Encuestas", poll: "Encuesta", noPolls: "No tienes encuestas.",
      pollsToVote: "Pendientes de tu voto", pollsOther: "Otras encuestas",
      voteNow: "Por votar", voted: "Has votado", notVoted: "No votaste",
      awaiting: "Pendiente de publicar", resultPublished: "Resultado publicado", pollCancelled: "Anulada",
      closesOn: "Cierra {date}", closedOn: "Cerró {date}",
      closesAt: "Cierre de la votación", publishedAt: "Resultado publicado el",
      chooseOption: "Elige una opción", chooseFirst: "Elige una opción antes de votar.",
      vote: "Votar", voting: "Votando…",
      confirmTitle: "Confirma tu voto", confirmChoice: "Vas a votar",
      confirmWarning: "El voto es anónimo y, una vez emitido, no se puede cambiar ni retirar.",
      confirmVote: "Confirmar el voto", chooseAgain: "Elegir otra vez",
      votedNotice: "Has votado. El voto es anónimo: nadie, tampoco esta aplicación, puede saber qué elegiste.",
      alreadyVoted: "Ya habías votado en esta encuesta. El voto no se puede cambiar.",
      awaitingNotice: "Votación cerrada, pendiente de publicar. La junta publicará el resultado.",
      missedNotice: "La votación se cerró sin que votaras.",
      cancelledPoll: "Esta encuesta se ha anulado.", reason: "Motivo",
      provisional: "Recuento provisional", provisionalHint: "Puede cambiar hasta el cierre de la votación.",
      finalResult: "Resultado definitivo",
      votesCast: "Votos emitidos: {cast} de {recipients} convocados",
      participation: "Han votado {voted} de {recipients} convocados",
      turnout: "Participación", oneVote: "1 voto", votesCount: "{n} votos", noVotesYet: "Todavía no hay votos.",
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
      language: "Idioma", settings: "Ajustos", today: "Hui", tomorrow: "Demà",
      greeting: "Hola, {name}",
      polls: "Enquestes", poll: "Enquesta", noPolls: "No tens enquestes.",
      pollsToVote: "Pendents del teu vot", pollsOther: "Altres enquestes",
      voteNow: "Per votar", voted: "Has votat", notVoted: "No vas votar",
      awaiting: "Pendent de publicar", resultPublished: "Resultat publicat", pollCancelled: "Anul·lada",
      closesOn: "Tanca {date}", closedOn: "Va tancar {date}",
      closesAt: "Tancament de la votació", publishedAt: "Resultat publicat el",
      chooseOption: "Tria una opció", chooseFirst: "Tria una opció abans de votar.",
      vote: "Votar", voting: "Votant…",
      confirmTitle: "Confirma el teu vot", confirmChoice: "Vas a votar",
      confirmWarning: "El vot és anònim i, una vegada emés, no es pot canviar ni retirar.",
      confirmVote: "Confirmar el vot", chooseAgain: "Triar una altra vegada",
      votedNotice: "Has votat. El vot és anònim: ningú, tampoc aquesta aplicació, pot saber què vas triar.",
      alreadyVoted: "Ja havies votat en aquesta enquesta. El vot no es pot canviar.",
      awaitingNotice: "Votació tancada, pendent de publicar. La junta publicarà el resultat.",
      missedNotice: "La votació es va tancar sense que votares.",
      cancelledPoll: "Aquesta enquesta s'ha anul·lat.", reason: "Motiu",
      provisional: "Recompte provisional", provisionalHint: "Pot canviar fins al tancament de la votació.",
      finalResult: "Resultat definitiu",
      votesCast: "Vots emesos: {cast} de {recipients} convocats",
      participation: "Han votat {voted} de {recipients} convocats",
      turnout: "Participació", oneVote: "1 vot", votesCount: "{n} vots", noVotesYet: "Encara no hi ha vots.",
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
      language: "Language", settings: "Settings", today: "Today", tomorrow: "Tomorrow",
      greeting: "Hello, {name}",
      polls: "Polls", poll: "Poll", noPolls: "You have no polls.",
      pollsToVote: "Waiting for your vote", pollsOther: "Other polls",
      voteNow: "To vote", voted: "You voted", notVoted: "You did not vote",
      awaiting: "Awaiting publication", resultPublished: "Result published", pollCancelled: "Cancelled",
      closesOn: "Closes {date}", closedOn: "Closed {date}",
      closesAt: "Voting deadline", publishedAt: "Result published on",
      chooseOption: "Choose an option", chooseFirst: "Choose an option before voting.",
      vote: "Vote", voting: "Voting…",
      confirmTitle: "Confirm your vote", confirmChoice: "You are voting for",
      confirmWarning: "Your vote is anonymous and, once cast, cannot be changed or withdrawn.",
      confirmVote: "Cast my vote", chooseAgain: "Choose again",
      votedNotice: "You have voted. The vote is anonymous: nobody, not even this app, can tell what you chose.",
      alreadyVoted: "You had already voted in this poll. The vote cannot be changed.",
      awaitingNotice: "Voting closed, awaiting publication. The board will publish the result.",
      missedNotice: "Voting closed before you voted.",
      cancelledPoll: "This poll has been cancelled.", reason: "Reason",
      provisional: "Provisional count", provisionalHint: "It may change until voting closes.",
      finalResult: "Final result",
      votesCast: "Votes cast: {cast} of {recipients} invited",
      participation: "{voted} of {recipients} invited have voted",
      turnout: "Turnout", oneVote: "1 vote", votesCount: "{n} votes", noVotesYet: "No votes yet.",
    },
  };

  const read = (key) => { try { return localStorage.getItem(key); } catch { return null; } };
  const write = (key, value) => {
    try { value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value); } catch { /* modo privado */ }
  };
  const readJSON = (key) => { try { return JSON.parse(read(key) || "null"); } catch { return null; } };

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
    polls: [],
    /* Encuesta abierta en detalle. `pollId` sin `poll` significa que se esta
       descargando o que fallo la descarga. */
    poll: null,
    pollId: null,
    /* La opcion marcada solo vive en memoria mientras se confirma: nunca se
       guarda ni se muestra despues de votar, porque el voto es anonimo. */
    pollChoice: null,
    confirming: false,
    banner: null,
    busy: false,
    /* Selector que recibe el foco tras pintar: el contenido se reemplaza entero
       y sin esto un lector de pantalla se quedaria sin saber donde esta. */
    focus: null,
    loading: false,
    /* Lo ultimo que se supo de la asociacion: pinta el acceso con su marca
       antes de que haya sesion con la que preguntarla. */
    branding: readJSON(STORE.branding),
    logo: null,
  };

  const t = (key) => STRINGS[state.lang][key] ?? key;
  /** Texto con huecos `{nombre}`. */
  const tf = (key, values) => t(key).replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
  const association = () => state.associations.find((item) => item.id === state.associationId) || state.associations[0];

  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* --- color de la asociacion --- */

  const parseHex = (value) => {
    const match = /^#?([0-9a-f]{6})$/i.exec(String(value ?? "").trim());
    if (!match) return null;
    const number = parseInt(match[1], 16);
    return { r: (number >> 16) & 255, g: (number >> 8) & 255, b: number & 255 };
  };
  const toHex = (c) =>
    "#" + [c.r, c.g, c.b].map((v) => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, "0")).join("");
  const mix = (a, b, amount) => ({
    r: a.r + (b.r - a.r) * amount,
    g: a.g + (b.g - a.g) * amount,
    b: a.b + (b.b - a.b) * amount,
  });
  const channel = (value) => {
    const v = value / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  const luminance = (c) => 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);
  const contrast = (a, b) => {
    const one = luminance(a);
    const two = luminance(b);
    return (Math.max(one, two) + 0.05) / (Math.min(one, two) + 0.05);
  };

  const WHITE = { r: 255, g: 255, b: 255 };
  const BLACK = { r: 0, g: 0, b: 0 };

  /** El texto que se lee sobre un fondo de marca: blanco o casi negro, el que mas contraste dé. */
  const inkOn = (background) => (contrast(background, WHITE) >= contrast(background, { r: 16, g: 24, b: 29 }) ? WHITE : { r: 16, g: 24, b: 29 });

  /** Acerca el color a blanco o a negro hasta que se lea sobre todos los fondos dados. */
  function legible(color, backgrounds, target = 4.5) {
    const towards = luminance(backgrounds[0]) > 0.5 ? BLACK : WHITE;
    let candidate = color;
    for (let step = 0; step <= 20; step += 1) {
      if (backgrounds.every((background) => contrast(candidate, background) >= target)) return candidate;
      candidate = mix(color, towards, step / 20);
    }
    return towards;
  }

  const prefersDark = () => window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;

  function aplicarMarca(brand) {
    const style = document.documentElement.style;
    const dark = prefersDark();
    const surface = dark ? { r: 0x13, g: 0x1c, b: 0x22 } : WHITE;

    const primary = parseHex(brand?.primary_color) || parseHex(DEFAULT_BRAND.primary_color);
    const secondary = parseHex(brand?.secondary_color) || parseHex(DEFAULT_BRAND.secondary_color);

    const soft = mix(primary, surface, dark ? 0.84 : 0.9);
    const text = legible(primary, [surface, soft]);

    style.setProperty("--brand", toHex(primary));
    style.setProperty("--brand-ink", toHex(inkOn(primary)));
    style.setProperty("--brand-deep", toHex(mix(primary, BLACK, 0.3)));
    style.setProperty("--brand-text", toHex(text));
    style.setProperty("--brand-soft", toHex(soft));
    style.setProperty("--accent", toHex(secondary));
    style.setProperty("--accent-ink", toHex(inkOn(secondary)));

    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", toHex(primary));
  }

  /** Guarda marca y logotipo para que el acceso ya tenga la cara de la banda. */
  function recordarMarca(assoc, logoDataUrl) {
    if (!assoc) return;
    const stored = {
      name: assoc.name,
      motto: assoc.motto || "",
      primary_color: assoc.primary_color,
      secondary_color: assoc.secondary_color,
      logo: logoDataUrl ?? (state.branding?.name === assoc.name ? state.branding.logo : null),
    };
    state.branding = stored;
    write(STORE.branding, JSON.stringify(stored));
  }

  async function cargarLogotipo(assoc) {
    if (state.logo) { URL.revokeObjectURL(state.logo); state.logo = null; }
    if (!assoc?.logo_url) { recordarMarca(assoc, null); return; }
    try {
      const response = await fetch(assoc.logo_url, { headers: { Authorization: `Token ${state.token}` } });
      if (!response.ok) return;
      const blob = await response.blob();
      state.logo = URL.createObjectURL(blob);
      /* Solo se guarda si cabe holgadamente en localStorage. */
      if (blob.size <= 120 * 1024) {
        const reader = new FileReader();
        reader.onload = () => recordarMarca(assoc, String(reader.result));
        reader.readAsDataURL(blob);
      } else {
        recordarMarca(assoc, null);
      }
    } catch { /* el logotipo no es critico */ }
  }

  const initials = (name) =>
    String(name || "")
      .split(/\s+/)
      .filter((word) => word.length > 2 || /^[A-ZÀ-Ý]/.test(word))
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase() || "♪";

  const logoMark = (name, source, extra = "") => {
    const classes = `logo${extra ? ` ${extra}` : ""}`;
    return source
      ? `<img class="${classes}" src="${esc(source)}" alt="">`
      : `<span class="${classes}" aria-hidden="true">${esc(initials(name))}</span>`;
  };

  /* --- fechas --- */

  const zone = () => association()?.timezone || undefined;

  function formatDate(value, withTime = true) {
    if (!value) return "—";
    const options = withTime
      ? { dateStyle: "full", timeStyle: "short", timeZone: zone() }
      : { dateStyle: "full", timeZone: zone() };
    try { return new Intl.DateTimeFormat(state.lang, options).format(new Date(value)); }
    catch { return new Date(value).toLocaleString(); }
  }

  const parts = (value, options) => {
    try { return new Intl.DateTimeFormat(state.lang, { ...options, timeZone: zone() }).formatToParts(new Date(value)); }
    catch { return new Intl.DateTimeFormat(state.lang, options).formatToParts(new Date(value)); }
  };
  const part = (value, options, type) => parts(value, options).find((item) => item.type === type)?.value ?? "";

  /** Dia natural en la zona de la asociacion, comparable como texto. */
  const dayKey = (value) => {
    try { return new Intl.DateTimeFormat("en-CA", { timeZone: zone(), year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(value)); }
    catch { return new Date(value).toISOString().slice(0, 10); }
  };

  function relativeDay(value) {
    const now = new Date();
    const key = dayKey(value);
    if (key === dayKey(now)) return t("today");
    if (key === dayKey(new Date(now.getTime() + 86400000))) return t("tomorrow");
    return "";
  }

  const monthLabel = (value) => {
    const label = `${part(value, { month: "long" }, "month")} ${part(value, { year: "numeric" }, "year")}`;
    return label.charAt(0).toUpperCase() + label.slice(1);
  };

  const shortDateTime = (value) => {
    try {
      return new Intl.DateTimeFormat(state.lang, {
        day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: zone(),
      }).format(new Date(value));
    } catch { return formatDate(value); }
  };

  const time = (value) => {
    try { return new Intl.DateTimeFormat(state.lang, { timeStyle: "short", timeZone: zone() }).format(new Date(value)); }
    catch { return ""; }
  };

  /* --- api --- */

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

  /* --- piezas --- */

  const banner = () => `
    <p class="notice${state.banner.kind === "error" ? " error" : ""}">
      <span class="note-dot"></span><span>${esc(state.banner.text)}</span>
    </p>`;

  const inlineNotice = (text, kind = "") => `
    <span class="notice${kind ? ` ${kind}` : ""}"><span class="note-dot"></span><span>${esc(text)}</span></span>`;

  const languageSelect = () => `
    <select data-action="language" aria-label="${esc(t("language"))}">
      ${["es", "ca", "en"].map((code) =>
        `<option value="${code}"${code === state.lang ? " selected" : ""}>${{ es: "Castellano", ca: "Valencià", en: "English" }[code]}</option>`
      ).join("")}
    </select>`;

  const empty = (mark, text) => `
    <div class="empty">
      <div class="empty__mark" aria-hidden="true">${mark}</div>
      <p>${esc(text)}</p>
    </div>`;

  const skeleton = () => `<div class="skeleton" aria-hidden="true"><span></span><span></span><span></span></div>`;

  /* --- vistas --- */

  function viewLogin() {
    const brand = state.branding;
    return `
      <div class="auth">
        <div class="auth__brand">
          ${logoMark(brand?.name, brand?.logo, "logo--xl")}
          <h1>${esc(brand?.name || t("appName"))}</h1>
          ${brand?.motto ? `<p class="motto">${esc(brand.motto)}</p>` : ""}
        </div>
        ${state.banner ? banner() : ""}
        <form class="stack" data-form="login">
          <div class="field">
            <label for="email">${esc(t("email"))}</label>
            <input id="email" name="email" type="email" autocomplete="username" required autocapitalize="none" spellcheck="false">
          </div>
          <div class="field">
            <label for="password">${esc(t("password"))}</label>
            <input id="password" name="password" type="password" autocomplete="current-password" required>
          </div>
          <button class="button" type="submit"${state.busy ? " disabled" : ""}>
            ${esc(state.busy ? t("signingIn") : t("signIn"))}
          </button>
        </form>
        <div class="auth__foot">
          ${languageSelect()}
          ${brand?.name ? `<p class="wordmark">${esc(t("appName"))}</p>` : ""}
        </div>
      </div>`;
  }

  function shell(content) {
    const unread = state.notifications.filter((item) => !item.read_at).length;
    const toVote = state.polls.filter(votable).length;
    const current = association();
    const picker = state.associations.length > 1
      ? `<select class="picker" data-action="association" aria-label="${esc(t("association"))}">
           ${state.associations.map((item) =>
             `<option value="${esc(item.id)}"${item.id === state.associationId ? " selected" : ""}>${esc(item.name)}</option>`
           ).join("")}
         </select>`
      : "";
    const name = state.account?.display_name || "";
    return `
      <header class="topbar">
        <div class="topbar__row">
          ${logoMark(current?.name, state.logo)}
          <div class="topbar__id">
            <h1>${esc(current?.name || t("appName"))}</h1>
            ${current?.motto ? `<p class="motto">${esc(current.motto)}</p>` : ""}
          </div>
        </div>
        ${name ? `<p class="greeting">${esc(t("greeting").replace("{name}", name))}</p>` : ""}
        ${picker}
      </header>
      <nav class="tabs">
        <button data-tab="agenda"${state.tab === "agenda" ? ' aria-current="page"' : ""}>${esc(t("agenda"))}</button>
        <button data-tab="inbox"${state.tab === "inbox" ? ' aria-current="page"' : ""}>${esc(t("inbox"))}${unread ? `<span class="badge">${unread}</span>` : ""}</button>
        ${canSeePolls() ? `<button data-tab="polls"${state.tab === "polls" ? ' aria-current="page"' : ""}>${esc(t("polls"))}${toVote ? `<span class="badge">${toVote}</span>` : ""}</button>` : ""}
        <button data-tab="profile"${state.tab === "profile" ? ' aria-current="page"' : ""}>${esc(t("profile"))}</button>
      </nav>
      <main>${state.banner ? banner() : ""}${content}</main>`;
  }

  function activityCard(activity) {
    const mine = activity.invitations?.[0];
    const response = mine?.response || "pending";
    const cancelled = activity.status === "cancelled";
    const when = relativeDay(activity.starts_at);
    const chips = [
      `<span class="chip ${esc(response)}">${esc(t(response))}</span>`,
      cancelled ? `<span class="chip cancelled">${esc(t("cancelled"))}</span>` : "",
      activity.is_mandatory ? `<span class="chip mandatory">${esc(t("mandatory"))}</span>` : "",
    ].filter(Boolean).join("");

    return `
      <button class="card act act--${esc(cancelled ? "cancelled" : response)}" data-activity="${esc(activity.id)}">
        <span class="date">
          <span class="date__dow">${esc(part(activity.starts_at, { weekday: "short" }, "weekday"))}</span>
          <span class="date__day">${esc(part(activity.starts_at, { day: "numeric" }, "day"))}</span>
          <span class="date__mon">${esc(part(activity.starts_at, { month: "short" }, "month"))}</span>
        </span>
        <span class="act__body">
          <span class="act__meta">${esc(t(activity.kind))}${when ? ` · ${esc(when)}` : ""} · ${esc(time(activity.starts_at))}</span>
          <span class="act__title">${esc(activity.title)}</span>
          ${activity.location ? `<span class="act__where">${esc(activity.location)}</span>` : ""}
          <span class="chips">${chips}</span>
          ${mine?.needs_reconfirmation ? inlineNotice(t("reconfirm")) : ""}
        </span>
      </button>`;
  }

  function viewAgenda() {
    if (state.loading && !state.activities.length) return shell(skeleton());
    if (!state.activities.length) return shell(empty("♪", t("noActivities")));

    let month = "";
    const blocks = state.activities.map((activity) => {
      const label = monthLabel(activity.starts_at);
      const heading = label === month ? "" : `<h2 class="month">${esc(label)}</h2>`;
      month = label;
      return heading + activityCard(activity);
    });
    return shell(blocks.join(""));
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
      ? `<h3 class="section-title">${esc(t("programme"))}</h3>
         <ol class="programme">${activity.programme.map((item) =>
           `<li><span>${esc(item.title)}${item.notes ? ` <span class="muted">— ${esc(item.notes)}</span>` : ""}</span></li>`).join("")}</ol>`
      : "";

    const answer = mine
      ? `<section class="answer">
           <div class="answer__head">
             <h3>${esc(t("yourAnswer"))}</h3>
             <span class="chip ${esc(mine.response)}">${esc(t(mine.response))}</span>
           </div>
           ${mine.response_note ? `<p class="muted">${esc(t("note"))}: ${esc(mine.response_note)}</p>` : ""}
           ${closed ? "" : `
             <form class="stack" data-form="respond" data-invitation="${esc(mine.id)}">
               ${activity.is_mandatory ? `
                 <div class="field">
                   <label for="note">${esc(t("reasonLabel"))}</label>
                   <textarea id="note" name="note" rows="2" maxlength="500"></textarea>
                 </div>` : ""}
               <div class="actions">
                 <button class="button" type="submit" name="response" value="accepted"${state.busy ? " disabled" : ""}>${esc(t("accept"))}</button>
                 <button class="button ghost" type="submit" name="response" value="declined"${state.busy ? " disabled" : ""}>${esc(t("decline"))}</button>
               </div>
             </form>`}
         </section>`
      : "";

    return shell(`
      <button class="back" data-action="back">← ${esc(t("back"))}</button>
      <article class="detail">
        <p class="detail__kicker">${esc(t(activity.kind))}${activity.is_mandatory ? ` · ${esc(t("mandatory"))}` : ""}</p>
        <h2>${esc(activity.title)}</h2>
        ${activity.status === "cancelled" ? inlineNotice(t("cancelledNotice"), "error") : ""}
        ${mine?.needs_reconfirmation ? inlineNotice(t("reconfirm")) : ""}
        ${deadlinePassed && activity.status === "published" ? inlineNotice(t("deadlinePassed")) : ""}
        <dl class="facts">${facts.map(([term, value]) => `<div><dt>${esc(term)}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>
        ${programme}
        ${answer}
      </article>`);
  }

  function viewInbox() {
    if (state.loading && !state.notifications.length) return shell(skeleton());
    if (!state.notifications.length) return shell(empty("✉", t("noNotices")));
    return shell(state.notifications.map((notice) => `
      <button class="card act act--${notice.read_at ? "read" : "unread"}" data-notification="${esc(notice.id)}">
        <span class="act__body">
          <span class="act__meta act__meta--plain">${esc(shortDateTime(notice.created_at))}</span>
          <span class="act__title">${esc(notice.title)}</span>
          <span class="act__where">${esc(notice.body).replace(/\n/g, "<br>")}</span>
        </span>
      </button>`).join(""));
  }


  /* --- encuestas ---
     El cliente nunca sabe que eligio la persona: la API solo dice si ha votado
     (`has_voted`) y el recuento anonimo. Lo que se ve aqui sale de ahi. */

  const canSeePolls = () => {
    const granted = association()?.permissions;
    return !Array.isArray(granted) || granted.includes("polls.view") || granted.includes("*");
  };

  const pollClosed = (poll) => new Date(poll.closes_at) <= new Date();
  /** El servidor dice si se puede votar; el reloj local solo lo apaga antes. */
  const votable = (poll) => Boolean(poll.can_vote) && poll.status === "open" && !pollClosed(poll);

  /** Fase de la encuesta desde el punto de vista del musico. */
  function pollPhase(poll) {
    if (poll.status === "cancelled") return "cancelled";
    if (poll.status === "published") return "published";
    return pollClosed(poll) ? "awaiting" : "open";
  }

  function pollChip(poll) {
    const phase = pollPhase(poll);
    if (phase === "cancelled") return `<span class="chip cancelled">${esc(t("pollCancelled"))}</span>`;
    if (phase === "published") return `<span class="chip final">${esc(t("resultPublished"))}</span>`;
    const own = votable(poll)
      ? `<span class="chip pending">${esc(t("voteNow"))}</span>`
      : poll.has_voted ? `<span class="chip accepted">${esc(t("voted"))}</span>` : "";
    return own + (phase === "awaiting" ? `<span class="chip">${esc(t("awaiting"))}</span>` : "");
  }

  function pollRail(poll) {
    const phase = pollPhase(poll);
    if (phase === "cancelled") return "cancelled";
    if (votable(poll)) return "pending";
    if (phase === "published") return "final";
    return poll.has_voted ? "accepted" : "read";
  }

  function pollCard(poll) {
    const when = tf(pollClosed(poll) ? "closedOn" : "closesOn", { date: shortDateTime(poll.closes_at) });
    return `
      <button class="card act act--${esc(pollRail(poll))}" data-poll="${esc(poll.id)}">
        <span class="date">
          <span class="date__dow">${esc(part(poll.closes_at, { weekday: "short" }, "weekday"))}</span>
          <span class="date__day">${esc(part(poll.closes_at, { day: "numeric" }, "day"))}</span>
          <span class="date__mon">${esc(part(poll.closes_at, { month: "short" }, "month"))}</span>
        </span>
        <span class="act__body">
          <span class="act__meta act__meta--plain">${esc(when)}</span>
          <span class="act__title">${esc(poll.question)}</span>
          <span class="chips">${pollChip(poll)}</span>
        </span>
      </button>`;
  }

  const loadError = () => `
    <div class="empty">
      <div class="empty__mark" aria-hidden="true">!</div>
      <p>${esc(t("loadFailed"))}</p>
      <button class="button ghost" data-action="retry">${esc(t("retry"))}</button>
    </div>`;

  function viewPolls() {
    if (state.loading && !state.polls.length) return shell(skeleton());
    if (!state.polls.length) return shell(state.banner?.kind === "error" ? loadError() : empty("?", t("noPolls")));

    const pending = state.polls.filter(votable);
    const rest = state.polls.filter((poll) => !votable(poll));
    const group = (title, items) => items.length
      ? `<h2 class="month">${esc(title)}</h2>${items.map(pollCard).join("")}`
      : "";
    return shell(group(t("pollsToVote"), pending) + group(t("pollsOther"), rest));
  }

  const votesLabel = (n) => (n === 1 ? t("oneVote") : tf("votesCount", { n }));

  function pollResults(poll) {
    const results = poll.results;
    if (!results) return "";
    const final = results.kind === "final";
    const cast = results.votes_cast || 0;
    const top = Math.max(0, ...results.options.map((option) => option.votes));
    const recipients = poll.participation?.recipients ?? 0;

    const rows = results.options.map((option) => {
      const share = cast ? Math.round((option.votes / cast) * 100) : 0;
      const lead = final && option.votes > 0 && option.votes === top;
      return `
        <li class="tally__row${lead ? " tally__row--lead" : ""}">
          <span class="tally__label">${esc(option.label)}</span>
          <span class="tally__count">${esc(votesLabel(option.votes))} · ${share}%</span>
          <span class="tally__bar" aria-hidden="true"><span style="width:${share}%"></span></span>
        </li>`;
    }).join("");

    return `
      <section class="tally${final ? " tally--final" : ""}" aria-labelledby="tally-title">
        <div class="answer__head">
          <h3 id="tally-title">${esc(t(final ? "finalResult" : "provisional"))}</h3>
        </div>
        <p class="tally__summary">${esc(tf("votesCast", { cast, recipients }))}</p>
        ${cast ? `<ol class="tally__list">${rows}</ol>` : `<p class="muted">${esc(t("noVotesYet"))}</p>`}
        ${final ? "" : `<p class="muted tally__hint">${esc(t("provisionalHint"))}</p>`}
      </section>`;
  }

  function voteForm(poll) {
    if (state.confirming) {
      const choice = poll.choices.find((option) => option.id === state.pollChoice);
      return `
        <section class="answer confirm" aria-labelledby="confirm-title">
          <h3 id="confirm-title" tabindex="-1">${esc(t("confirmTitle"))}</h3>
          <p class="confirm__choice"><span class="muted">${esc(t("confirmChoice"))}:</span> <strong>${esc(choice?.label)}</strong></p>
          ${inlineNotice(t("confirmWarning"))}
          <form data-form="confirm-vote">
            <div class="actions">
              <button class="button" type="submit"${state.busy ? " disabled" : ""}>${esc(state.busy ? t("voting") : t("confirmVote"))}</button>
              <button class="button ghost" type="button" data-action="vote-back"${state.busy ? " disabled" : ""}>${esc(t("chooseAgain"))}</button>
            </div>
          </form>
        </section>`;
    }
    const options = poll.choices.map((option, index) => `
      <label class="choice" for="choice-${index}">
        <input type="radio" id="choice-${index}" name="option" value="${esc(option.id)}"${option.id === state.pollChoice ? " checked" : ""}>
        <span>${esc(option.label)}</span>
      </label>`).join("");
    return `
      <section class="answer">
        <form class="stack" data-form="vote">
          <fieldset class="choices">
            <legend>${esc(t("chooseOption"))}</legend>
            ${options}
          </fieldset>
          <p class="muted confirm__hint">${esc(t("confirmWarning"))}</p>
          <div class="actions">
            <button class="button" type="submit"${state.busy ? " disabled" : ""}>${esc(t("vote"))}</button>
          </div>
        </form>
      </section>`;
  }

  function viewPoll() {
    const poll = state.poll;
    const back = `<button class="back" data-action="back">← ${esc(t("back"))}</button>`;
    if (!poll) {
      if (state.loading) return shell(back + skeleton());
      return shell(back + loadError());
    }

    const phase = pollPhase(poll);
    const recipients = poll.participation?.recipients ?? 0;
    const facts = [
      [t("closesAt"), formatDate(poll.closes_at)],
      poll.published_at ? [t("publishedAt"), formatDate(poll.published_at)] : null,
    ].filter(Boolean);

    const notices = [];
    if (phase === "cancelled") {
      notices.push(inlineNotice(t("cancelledPoll"), "error"));
    } else {
      if (poll.has_voted) notices.push(inlineNotice(t("votedNotice"), "ok"));
      else if (poll.has_voted === false && !votable(poll)) notices.push(inlineNotice(t("missedNotice")));
      if (phase === "awaiting") notices.push(inlineNotice(t("awaitingNotice")));
    }

    return shell(`
      ${back}
      <article class="detail">
        <p class="detail__kicker">${esc(t("poll"))}</p>
        <h2 id="poll-title" tabindex="-1">${esc(poll.question)}</h2>
        <div class="chips chips--detail">${pollChip(poll)}</div>
        <div class="notices" id="poll-notices" tabindex="-1">${notices.join("")}</div>
        ${poll.description ? `<p class="lead">${esc(poll.description).replace(/\n/g, "<br>")}</p>` : ""}
        <dl class="facts">
          ${facts.map(([term, value]) => `<div><dt>${esc(term)}</dt><dd>${esc(value)}</dd></div>`).join("")}
          ${phase === "cancelled" && poll.cancel_reason
            ? `<div><dt>${esc(t("reason"))}</dt><dd>${esc(poll.cancel_reason)}</dd></div>` : ""}
          ${phase === "awaiting" && poll.participation
            ? `<div><dt>${esc(t("turnout"))}</dt><dd>${esc(tf("participation", { voted: poll.participation.voted, recipients }))}</dd></div>` : ""}
        </dl>
        ${votable(poll) ? voteForm(poll) : ""}
        ${pollResults(poll)}
      </article>`);
  }

  function viewProfile() {
    const member = state.member;
    const settings = `
      <section class="settings">
        <h3>${esc(t("settings"))}</h3>
        <div class="field">
          <label for="lang">${esc(t("language"))}</label>
          ${languageSelect().replace("<select", '<select id="lang"')}
        </div>
        <button class="button quiet" data-action="signout">${esc(t("signOut"))}</button>
      </section>`;

    if (!member) return shell(empty("!", t("loadFailed")) + settings);

    const full = `${member.first_name} ${member.last_name}`.trim();
    const instruments = member.instruments?.length
      ? member.instruments.map((item) => esc(item.name || item)).join(", ")
      : esc(t("noInstruments"));
    return shell(`
      <div class="profile__head">
        <span class="avatar" aria-hidden="true">${esc(initials(full))}</span>
        <h2>${esc(full)}</h2>
      </div>
      <dl class="facts">
        <div><dt>${esc(t("email"))}</dt><dd>${esc(member.email || "—")}</dd></div>
        <div><dt>${esc(t("phone"))}</dt><dd>${esc(member.phone || "—")}</dd></div>
        <div><dt>${esc(t("instruments"))}</dt><dd>${instruments}</dd></div>
      </dl>
      ${settings}`);
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
    const current = association();
    aplicarMarca(current);
    recordarMarca(current);
    await cargarLogotipo(current);
  }

  async function loadTab() {
    state.loading = true;
    try {
      if (state.tab === "agenda") {
        const page = await api("/activities/");
        state.activities = page.results || page;
      } else if (state.tab === "inbox") {
        const page = await api("/notifications/", { association: false });
        state.notifications = page.results || page;
      } else if (state.tab === "polls") {
        const page = await api("/polls/");
        state.polls = page.results || page;
      } else if (state.tab === "profile") {
        state.member = await api("/members/me/");
      }
      state.banner = null;
    } catch (error) {
      if (error.message === "unauthorized") return;
      state.banner = { kind: "error", text: navigator.onLine ? problem(error) : t("offline") };
    } finally {
      state.loading = false;
    }
  }

  /** Encuestas en segundo plano, para que la pestana diga cuantas esperan voto. */
  async function refreshPolls() {
    if (!canSeePolls()) { state.polls = []; return; }
    try {
      const page = await api("/polls/");
      state.polls = page.results || page;
    } catch { /* solo alimenta el contador */ }
  }

  function closePoll() {
    state.poll = null; state.pollId = null; state.pollChoice = null; state.confirming = false;
  }

  async function openPoll(id) {
    closePoll();
    state.activity = null;
    state.pollId = id;
    state.poll = state.polls.find((item) => item.id === id) || null;
    state.focus = "#poll-title";
    state.banner = null;
    state.loading = true;
    render();
    try {
      const fresh = await api(`/polls/${id}/`);
      if (state.pollId !== id) return;
      state.poll = fresh;
      state.polls = state.polls.some((item) => item.id === id)
        ? state.polls.map((item) => (item.id === id ? fresh : item))
        : state.polls;
    } catch (error) {
      if (error.message === "unauthorized" || state.pollId !== id) return;
      state.banner = { kind: "error", text: navigator.onLine ? problem(error) : t("offline") };
    } finally {
      state.loading = false;
    }
    if (state.pollId === id) { state.focus = "#poll-title"; render(); }
  }

  async function openActivity(id) {
    closePoll();
    const known = state.activities.find((item) => item.id === id);
    if (known) { state.activity = known; render(); return; }
    try {
      state.activity = await api(`/activities/${id}/`);
      render();
    } catch (error) {
      if (error.message === "unauthorized") return;
      state.banner = { kind: "error", text: navigator.onLine ? problem(error) : t("offline") };
      render();
    }
  }

  async function castVote() {
    const poll = state.poll;
    const optionId = state.pollChoice;
    state.busy = true; state.banner = null; render();
    try {
      const fresh = await api(`/polls/${poll.id}/vote/`, { method: "POST", body: { option_id: optionId } });
      state.poll = fresh;
      state.focus = "#poll-notices";
    } catch (error) {
      if (error.message === "unauthorized") { state.busy = false; return; }
      state.banner = {
        kind: "error",
        text: error.status === 409 ? t("alreadyVoted") : navigator.onLine ? problem(error) : t("offline"),
      };
      /* Otra pestana, otro dispositivo o el plazo: lo que manda es el servidor. */
      try { state.poll = await api(`/polls/${poll.id}/`); } catch { /* se queda lo que habia */ }
      state.focus = "#poll-title";
    }
    /* La eleccion se olvida pase lo que pase. */
    state.pollChoice = null;
    state.confirming = false;
    state.busy = false;
    state.polls = state.polls.map((item) => (item.id === state.poll.id ? state.poll : item));
    render();
  }

  function signOut({ silent = false } = {}) {
    state.token = null; state.account = null; state.activities = []; state.notifications = [];
    state.activity = null; state.member = null; state.polls = [];
    closePoll();
    if (state.logo) { URL.revokeObjectURL(state.logo); state.logo = null; }
    write(STORE.token, null);
    if (!silent) state.banner = null;
    render();
  }

  /* --- render y eventos --- */

  const root = document.getElementById("app");

  function render() {
    if (!state.token) { root.innerHTML = viewLogin(); return; }
    if (state.pollId) root.innerHTML = viewPoll();
    else if (state.activity) root.innerHTML = viewActivity();
    else root.innerHTML = { agenda: viewAgenda, inbox: viewInbox, polls: viewPolls, profile: viewProfile }[state.tab]();
    if (state.focus) {
      const target = root.querySelector(state.focus);
      state.focus = null;
      target?.focus();
    }
  }

  root.addEventListener("click", async (event) => {
    const target = event.target.closest("[data-tab], [data-activity], [data-poll], [data-notification], [data-action]");
    if (!target) return;

    if (target.dataset.tab) {
      state.tab = target.dataset.tab; state.activity = null; closePoll();
      render(); await loadTab(); render(); return;
    }
    if (target.dataset.poll) { await openPoll(target.dataset.poll); return; }
    if (target.dataset.activity) {
      state.activity = state.activities.find((item) => item.id === target.dataset.activity);
      render(); return;
    }
    if (target.dataset.notification) {
      const id = target.dataset.notification;
      const notice = state.notifications.find((item) => item.id === id);
      try {
        const fresh = await api(`/notifications/${id}/`, { association: false });
        state.notifications = state.notifications.map((item) => (item.id === fresh.id ? fresh : item));
      } catch { /* leerlo no es critico */ }
      /* Se abre por el campo, no por `deep_link`, cuyo formato es del cliente movil. */
      if (notice?.poll) { await openPoll(notice.poll); return; }
      if (notice?.activity) { await openActivity(notice.activity); return; }
      render();
      return;
    }
    if (target.dataset.action === "signout") { signOut(); return; }
    if (target.dataset.action === "back") {
      const wasPoll = Boolean(state.pollId);
      state.activity = null; closePoll(); state.banner = null; render();
      if (wasPoll && state.tab === "polls") { await loadTab(); render(); }
      return;
    }
    if (target.dataset.action === "retry") {
      if (state.pollId) { await openPoll(state.pollId); return; }
      state.banner = null; render(); await loadTab(); render(); return;
    }
    if (target.dataset.action === "vote-back") {
      state.confirming = false; state.focus = 'input[name="option"]:checked'; render(); return;
    }
  });

  root.addEventListener("change", async (event) => {
    if (event.target.matches?.('input[name="option"]')) { state.pollChoice = event.target.value; return; }
    const select = event.target.closest("select[data-action]");
    if (!select) return;
    if (select.dataset.action === "language") {
      state.lang = select.value; write(STORE.lang, state.lang);
      document.documentElement.lang = state.lang;
      render(); await loadTab(); render(); return;
    }
    if (select.dataset.action === "association") {
      state.associationId = select.value; write(STORE.association, state.associationId);
      state.activity = null; closePoll(); state.polls = [];
      const current = association();
      aplicarMarca(current);
      recordarMarca(current);
      render();
      await Promise.all([cargarLogotipo(current), loadTab(), state.tab === "polls" ? null : refreshPolls()]);
      render();
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
        render(); await Promise.all([loadTab(), refreshPolls()]); render();
      } catch (error) {
        state.busy = false;
        state.banner = { kind: "error", text: error.status === 400 || error.status === 401 ? t("badCredentials") : problem(error) };
        render();
      }
      return;
    }

    if (form.dataset.form === "vote") {
      const picked = form.elements.option?.value || state.pollChoice;
      if (!picked) {
        state.banner = { kind: "error", text: t("chooseFirst") };
        state.focus = 'input[name="option"]';
        render(); return;
      }
      state.pollChoice = picked; state.confirming = true; state.banner = null;
      state.focus = "#confirm-title";
      render(); return;
    }

    if (form.dataset.form === "confirm-vote") {
      if (!state.poll || !state.pollChoice) { state.confirming = false; render(); return; }
      await castVote();
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
  window.matchMedia?.("(prefers-color-scheme: dark)")
    .addEventListener?.("change", () => aplicarMarca(association() || state.branding));

  document.documentElement.lang = state.lang;
  aplicarMarca(state.branding);
  render();
  if (state.token) {
    loadSession()
      .then(() => { render(); return Promise.all([loadTab(), state.tab === "polls" ? null : refreshPolls()]); })
      .then(render)
      .catch(() => render());
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/app/sw.js").catch(() => {}));
  }
})();
