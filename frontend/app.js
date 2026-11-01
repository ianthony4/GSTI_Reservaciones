// ReservaYa - frontend (consume la API REST con fetch)
// API_BASE viene de config.js: "" = mismo servidor; en GitHub Pages, la URL pública de la API.
const API_BASE = (window.RESERVAYA_API_BASE || "").replace(/\/$/, "");
const API = API_BASE + "/api";
const $ = (sel, root = document) => root.querySelector(sel);
let restaurants = [];

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" }, ...options,
  });
  const body = res.status === 204 ? null : await res.json();
  if (!res.ok) {
    let detail = body && body.detail;
    if (Array.isArray(detail)) detail = detail.map(d => d.msg.replace("Value error, ", "")).join(". ");
    throw new Error(detail || `Error ${res.status}`);
  }
  return body;
}

function showMsg(el, text, type) {
  el.textContent = text;
  el.className = "msg" + (type ? " " + type : "") + (el.classList.contains("full") ? " full" : "");
}

const fmtDate = d => d.split("-").reverse().join("/");
const hhmm = t => t.slice(0, 5);
const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

function timeOptions(select, selected) {
  select.innerHTML = "";
  for (let h = 12; h <= 21; h++) {
    for (const m of ["00", "30"]) {
      if (h === 21 && m === "30") continue; // la reserva de 2 h debe acabar a las 23:00
      const v = `${String(h).padStart(2, "0")}:${m}`;
      select.add(new Option(v, v, false, v === selected));
    }
  }
}

function restaurantOptions(select, selectedId) {
  select.innerHTML = "";
  restaurants.forEach(r => select.add(new Option(r.name, r.id, false, r.id === selectedId)));
}

function dateLimits(input) {
  const today = new Date();
  const max = new Date(); max.setDate(today.getDate() + 60);
  input.min = iso(today); input.max = iso(max);
}

// ---------- Navegación ----------
document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === tab));
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === tab.dataset.view));
}));

// ---------- Sucursales ----------
async function loadRestaurants() {
  restaurants = await api("/restaurants");
  restaurantOptions($("#restaurant"));
  $("#branches").innerHTML = restaurants.map(r => `
    <div class="branch" data-id="${r.id}">
      <strong>${r.name}</strong>${r.address}<br>
      <span class="muted">Tel. ${r.phone} · ${hhmm(r.opening_time)}–${hhmm(r.closing_time)} · hasta ${r.max_capacity} pers.</span>
    </div>`).join("");
  document.querySelectorAll(".branch").forEach(b => b.addEventListener("click", () => {
    $("#restaurant").value = b.dataset.id; highlightBranch();
  }));
  highlightBranch();
}
function highlightBranch() {
  document.querySelectorAll(".branch").forEach(b => b.classList.toggle("selected", b.dataset.id === $("#restaurant").value));
}
$("#restaurant").addEventListener("change", highlightBranch);

// ---------- Reservar ----------
const form = $("#reserve-form");
const reserveMsg = $("#reserve-msg");

$("#check-btn").addEventListener("click", async () => {
  const f = new FormData(form);
  if (!f.get("date")) return showMsg(reserveMsg, "Selecciona una fecha.", "err");
  try {
    const q = new URLSearchParams({ date: f.get("date"), time: f.get("time"), party_size: f.get("party_size") });
    const r = await api(`/restaurants/${f.get("restaurant_id")}/availability?${q}`);
    showMsg(reserveMsg, r.available ? `✔ ${r.message}` : `✖ ${r.message}`, r.available ? "ok" : "err");
  } catch (e) { showMsg(reserveMsg, e.message, "err"); }
});

form.addEventListener("submit", async ev => {
  ev.preventDefault();
  if (!form.reportValidity()) return;
  const f = Object.fromEntries(new FormData(form));
  f.restaurant_id = Number(f.restaurant_id); f.party_size = Number(f.party_size);
  try {
    const r = await api("/reservations", { method: "POST", body: JSON.stringify(f) });
    const notifs = await api(`/reservations/${r.code}/notifications?email=${encodeURIComponent(r.customer_email)}`);
    showConfirmation(r, notifs[0]);
    showMsg(reserveMsg, "", "");
  } catch (e) { showMsg(reserveMsg, e.message, "err"); }
});

function showConfirmation(r, notif) {
  form.classList.add("hidden");
  $("#branches").classList.add("hidden");
  $("#conf-code").textContent = r.code;
  $("#conf-details").innerHTML = `
    <dt>Sucursal</dt><dd>${r.restaurant_name}</dd>
    <dt>Fecha</dt><dd>${fmtDate(r.date)}</dd>
    <dt>Hora</dt><dd>${hhmm(r.start_time)} – ${hhmm(r.end_time)}</dd>
    <dt>Personas</dt><dd>${r.party_size} (mesa ${r.table_number})</dd>
    <dt>Titular</dt><dd>${r.customer_name} · ${r.customer_email}</dd>`;
  $("#conf-notification").textContent = notif ? `Para: ${notif.recipient}\nAsunto: ${notif.subject}\n\n${notif.message}` : "";
  $("#confirmation").classList.remove("hidden");
  window.scrollTo(0, 0);
}

$("#new-reservation").addEventListener("click", () => {
  $("#confirmation").classList.add("hidden");
  form.classList.remove("hidden"); $("#branches").classList.remove("hidden");
});

// ---------- Mis reservas ----------
const mineMsg = $("#mine-msg");
let currentEmail = "";

$("#lookup-form").addEventListener("submit", async ev => {
  ev.preventDefault();
  currentEmail = $("#lookup-email").value.trim().toLowerCase();
  await loadMine();
});

async function loadMine() {
  const list = $("#my-reservations");
  list.innerHTML = "";
  try {
    const items = await api(`/customers/${encodeURIComponent(currentEmail)}/reservations`);
    showMsg(mineMsg, items.length ? "" : "No se encontraron reservas para ese correo.", items.length ? "" : "err");
    items.forEach(r => list.appendChild(renderReservation(r)));
    await loadRewards();
  } catch (e) { showMsg(mineMsg, e.message, "err"); }
}

// ---------- v1.1: recompensas ----------
async function loadRewards() {
  const box = $("#rewards");
  try {
    const s = await api(`/customers/${encodeURIComponent(currentEmail)}/rewards`);
    const names = { BRONCE: "Nivel Bronce", PLATA: "Nivel Plata", ORO: "Nivel Oro" };
    $("#rw-level").textContent = names[s.level]; $("#rw-level").className = "lvl-" + s.level;
    $("#rw-points").textContent = s.points;
    const span = s.next_level ? s.lifetime_points + s.points_to_next_level : s.lifetime_points || 1;
    $("#rw-bar").style.width = Math.min(100, (s.lifetime_points / span) * 100) + "%";
    $("#rw-next").textContent = s.next_level
      ? `${s.lifetime_points} puntos acumulados · te faltan ${s.points_to_next_level} para ${names[s.next_level]}. Ganas 10 puntos por cada reserva completada.`
      : `${s.lifetime_points} puntos acumulados · ¡estás en el nivel máximo!`;
    $("#rw-redeem").disabled = !s.can_redeem;
    $("#rw-history").innerHTML = s.transactions.map(t => `<li><span>${t.description}${t.coupon_code ? ` · <strong>${t.coupon_code}</strong>` : ""}</span>
      <span class="${t.points > 0 ? "plus" : "minus"}">${t.points > 0 ? "+" : ""}${t.points}</span></li>`).join("");
    box.classList.remove("hidden");
  } catch (e) { box.classList.add("hidden"); }
}

$("#rw-redeem").addEventListener("click", async () => {
  if (!confirm("¿Canjear 50 puntos por un cupón de 10 % de descuento?")) return;
  try {
    const r = await api(`/customers/${encodeURIComponent(currentEmail)}/rewards/redeem`, { method: "POST" });
    await loadRewards();
    showMsg(mineMsg, `Cupón ${r.coupon_code} generado (${r.benefit}). Te lo enviamos por correo.`, "ok");
  } catch (e) { showMsg(mineMsg, e.message, "err"); }
});

function renderReservation(r) {
  const node = $("#reservation-tpl").content.firstElementChild.cloneNode(true);
  const labels = { CONFIRMED: "Confirmada", CANCELLED: "Cancelada", COMPLETED: "Completada" };
  $(".res-code", node).textContent = r.code;
  const badge = $(".badge", node); badge.textContent = labels[r.status] || r.status; badge.classList.add(r.status);
  $(".res-branch", node).textContent = r.restaurant_name;
  $(".res-info", node).innerHTML = `<strong>${fmtDate(r.date)}</strong> · ${hhmm(r.start_time)}–${hhmm(r.end_time)} · ${r.party_size} personas · mesa ${r.table_number}` +
    (r.notes ? `<br><span class="muted">${r.notes.replace(/</g, "&lt;")}</span>` : "");
  const editable = r.status === "CONFIRMED";
  $(".act-edit", node).classList.toggle("hidden", !editable);
  $(".act-cancel", node).classList.toggle("hidden", !editable);

  const ef = $(".edit-form", node);
  $(".act-edit", node).addEventListener("click", () => {
    restaurantOptions(ef.restaurant_id, r.restaurant_id);
    dateLimits(ef.date); ef.date.value = r.date;
    timeOptions(ef.time, hhmm(r.start_time));
    ef.party_size.value = r.party_size; ef.notes.value = r.notes;
    ef.classList.remove("hidden");
  });
  $(".act-close", node).addEventListener("click", () => ef.classList.add("hidden"));
  ef.addEventListener("submit", async ev => {
    ev.preventDefault();
    const body = { email: currentEmail, restaurant_id: Number(ef.restaurant_id.value), date: ef.date.value,
                   time: ef.time.value, party_size: Number(ef.party_size.value), notes: ef.notes.value };
    try {
      await api(`/reservations/${r.code}`, { method: "PUT", body: JSON.stringify(body) });
      await loadMine(); showMsg(mineMsg, `Reserva ${r.code} modificada. Se envió una notificación.`, "ok");
    } catch (e) { showMsg(mineMsg, e.message, "err"); }
  });

  $(".act-cancel", node).addEventListener("click", async () => {
    if (!confirm(`¿Cancelar la reserva ${r.code}?`)) return;
    try {
      await api(`/reservations/${r.code}/cancel`, { method: "POST", body: JSON.stringify({ email: currentEmail }) });
      await loadMine(); showMsg(mineMsg, `Reserva ${r.code} cancelada. Se envió una notificación.`, "ok");
    } catch (e) { showMsg(mineMsg, e.message, "err"); }
  });

  $(".act-notifs", node).addEventListener("click", async () => {
    const ul = $(".notifs", node);
    if (!ul.classList.contains("hidden")) return ul.classList.add("hidden");
    const ns = await api(`/reservations/${r.code}/notifications?email=${encodeURIComponent(currentEmail)}`);
    ul.innerHTML = ns.map(n => `<li><strong>${n.subject}</strong> <span class="muted">· ${n.sent_at.slice(0, 16).replace("T", " ")}</span><pre></pre></li>`).join("");
    ul.querySelectorAll("pre").forEach((p, i) => p.textContent = ns[i].message);
    ul.classList.remove("hidden");
  });
  return node;
}

// ---------- Inicio ----------
document.querySelectorAll("a[data-api-docs]").forEach(a => a.href = API_BASE + "/docs");
dateLimits($("#date"));
const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
$("#date").value = iso(tomorrow);
timeOptions($("#time"), "19:00");
if (API_BASE) showMsg(reserveMsg, "Conectando con el servidor de la demo (puede tardar hasta 1 minuto si estaba en reposo)…", "");
loadRestaurants()
  .then(() => showMsg(reserveMsg, "", ""))
  .catch(e => showMsg(reserveMsg, "No se pudo conectar con la API: " + e.message, "err"));
