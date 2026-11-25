"use strict";

/* ============================================================ tiện ích */
const $ = (id) => document.getElementById(id);
const nf2 = new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nf1 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 });
const nf0 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });
const fmt = (x) => nf2.format(x);
const fmt1 = (x) => nf1.format(x);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const shortArea = (s) => String(s).replace(/^(Phường|Xã|Thị trấn)\s+/, "");
const signed = (x) => (x > 0 ? "+" : x < 0 ? "−" : "") + fmt1(Math.abs(x));
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

async function api(path, options) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail && typeof body.detail === "string" ? body.detail : "Không xử lý được yêu cầu.");
  return body;
}

// ?theme=light hoặc ?theme=dark để ép giao diện sáng / tối (mặc định theo hệ điều hành)
const THEME = new URLSearchParams(location.search).get("theme");
if (THEME === "light" || THEME === "dark") document.documentElement.dataset.theme = THEME;

let META = null;
const WIDE = 60, NARROW = 39;  // độ rộng khoảng / giá ước tính (%): ~phân vị 80% và 20% trên dữ liệu (src/intervals.py)
let furnishing = "";
let sourceCode = null;      // nguồn tin khi đọc từ link (mô hình có hiệu ứng nguồn); tự nhập thì để trống
let baseline = null;       // giá ước tính lần đầu của tin hiện tại, để so sánh khi thử thay đổi
let showingExample = false;

/* Lịch sử kiểm tra: chỉ lưu trong trình duyệt của người xem (localStorage), có thể trống / bị chặn */
const HISTORY_KEY = "tro-nay-co-ho-khong:lich-su";
const HISTORY_MAX = 6;
function readHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; }
}
function writeHistory(items) {
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(items)); } catch { /* bỏ qua: trình duyệt chặn lưu */ }
}
function remember(q, r) {
  const title = (q.text.split("\n")[0] || `${q.district}, ${q.size} m²`).trim().slice(0, 70);
  const key = `${q.district}|${q.size}|${q.text.trim()}`;
  const items = readHistory().filter((h) => h.key !== key);
  items.unshift({ key, title, q, price: r.price, verdict: r.verdict?.level || null });
  writeHistory(items.slice(0, HISTORY_MAX));
  drawHistory();
}
function drawHistory() {
  const items = readHistory();
  $("recent").hidden = items.length === 0;
  const tag = { high: "đắt hơn", low: "rẻ hơn", fair: "hợp lý" };
  $("recent-list").innerHTML = items.map((h, i) => `
    <button type="button" data-history="${i}">
      <span class="recent-title">${esc(h.title)}</span>
      <span class="recent-meta">${esc(shortArea(h.q.ward || h.q.district))} · ${fmt1(h.q.size)} m² · <b>${fmt(h.price)} tr</b>${h.verdict ? ` · ${tag[h.verdict]}` : ""}</span>
    </button>`).join("");
}

/* Các tin ví dụ do nhóm soạn để minh họa (không phải tin đăng thật) */
const EXAMPLES = [
  {
    district: "Hai Bà Trưng", size: 20, furnishing: "", asking: 4.5,
    text: "Cho thuê phòng trọ khép kín gần Bách Khoa, Kinh Tế\nPhòng 20m2 tầng 3, có điều hòa, nóng lạnh, giường tủ, kệ bếp. " +
      "Máy giặt chung, chỗ để xe tầng 1.\nGiờ giấc tự do, không chung chủ. Điện 4k/số, nước 100k/người.",
  },
  {
    district: "Cầu Giấy", size: 35, furnishing: "Nội thất đầy đủ", asking: 6.5,
    text: "Cho thuê căn hộ 1N1K full đồ, nhà mới xây\nPhòng ngủ riêng, phòng khách, bếp riêng, máy giặt riêng, ban công thoáng. " +
      "Tòa nhà có thang máy, khóa vân tay, camera an ninh 24/7.",
  },
  {
    district: "Đống Đa", size: 20, furnishing: "", asking: 1.8,
    text: "Homestay ở ghép giường tầng gần Ngã Tư Sở\nPhòng 6 người, giường tầng có rèm riêng, điều hòa, nóng lạnh, máy giặt. " +
      "Giá 1tr8/người bao điện nước, wifi.",
  },
];

/* ============================================================ điều hướng */
const VIEWS = ["dinh-gia", "ban-do", "mo-hinh"];
const loaded = {};

function route() {
  const v = VIEWS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "dinh-gia";
  VIEWS.forEach((name) => { $(`view-${name}`).hidden = name !== v; });
  document.querySelectorAll(".tab").forEach((t) => {
    if (t.dataset.view === v) t.setAttribute("aria-current", "page"); else t.removeAttribute("aria-current");
  });
  if (v === "ban-do") initMap();
  if (v === "mo-hinh") initAbout();
}

/* ============================================================ khởi động */
async function init() {
  META = await api("/api/meta");
  $("tagline").textContent =
    `Ước lượng từ ${META.n_listings.toLocaleString("vi-VN")} tin đăng phòng riêng trên Chợ Tốt, Phongtro123, Mogi · cập nhật ${META.updated}`;
  $("footer").textContent =
    `Mô hình ${META.model.name}. Sai số trung bình khoảng ${fmt(META.model.mae)} triệu (MAPE ${fmt1(META.model.mape)}%). ` +
    "Giá dựa trên tin đăng niêm yết, không phải giá chốt hợp đồng. Đồ án môn Nhập môn Học máy và Khai phá dữ liệu (IT3190).";

  $("district").innerHTML = META.districts.map((d) => `<option>${esc(d)}</option>`).join("");
  $("district").addEventListener("change", () => { fillWards(); predictSoon(); });
  $("ward").addEventListener("change", predictSoon);

  // "không rõ" là giá trị điền thiếu của mô hình, không hiển thị như một lựa chọn riêng
  const FURN_ORDER = ["Nhà trống", "Nội thất đầy đủ", "Nội thất cao cấp"];
  const furn = META.furnishings.filter((f) => f !== "không rõ")
    .sort((a, b) => FURN_ORDER.indexOf(a) - FURN_ORDER.indexOf(b));
  const opts = [["", "Không rõ"], ...furn.map((f) => [f, f.replace("Nội thất ", "").replace(/^./, (c) => c.toUpperCase())])];
  $("furnishing").innerHTML = opts.map(([v, l]) =>
    `<button type="button" data-value="${esc(v)}" aria-pressed="false">${esc(l)}</button>`).join("");
  $("furnishing").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    setFurnishing(b.dataset.value); predictSoon();
  });

  const sync = (from, to) => { $(to).value = $(from).value; predictSoon(); };
  $("size-range").addEventListener("input", () => sync("size-range", "size"));
  $("size").addEventListener("input", () => { $("size-range").value = Math.min(80, Math.max(8, $("size").value || 8)); predictSoon(); });
  $("asking").addEventListener("input", predictSoon);

  $("form").addEventListener("submit", (e) => { e.preventDefault(); markOwn(); baseline = null; predict(true); });
  $("fetch").addEventListener("click", importListing);
  $("url").addEventListener("input", () => { if (!$("url").value.trim()) sourceCode = null; });
  $("url").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); importListing(); } });
  document.querySelectorAll("[data-example]").forEach((b) =>
    b.addEventListener("click", () => loadExample(+b.dataset.example)));
  $("whatif").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-phrase]"); if (!b) return;
    $("text").value = `${$("text").value.trim()}\n${b.dataset.phrase}`;
    predict();
  });

  $("recent-list").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-history]"); if (!b) return;
    const h = readHistory()[+b.dataset.history]; if (!h) return;
    setForm(h.q); sourceCode = h.q.source || null;
    markOwn(); baseline = null; predict();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  $("recent-clear").addEventListener("click", () => { writeHistory([]); drawHistory(); });
  drawHistory();

  window.addEventListener("hashchange", route);
  route();
  loadExample(0, true);
}

function fillWards(selected) {
  const wards = META.wards[$("district").value] || [];
  $("ward").innerHTML = `<option value="">Cả quận</option>` + wards.map((w) => `<option>${esc(w)}</option>`).join("");
  if (selected && wards.includes(selected)) $("ward").value = selected;
}

function setFurnishing(v) {
  furnishing = v || "";
  document.querySelectorAll("#furnishing button").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.value === furnishing)));
}

function setForm(d) {
  if (d.district && META.districts.includes(d.district)) $("district").value = d.district;
  fillWards(d.ward);
  const size = Math.round(d.size || 20);
  $("size").value = size; $("size-range").value = Math.min(80, Math.max(8, size));
  setFurnishing(META.furnishings.includes(d.furnishing) ? d.furnishing : "");
  $("text").value = d.text || "";
  $("asking").value = d.asking ?? d.price ?? "";
}

function loadExample(i, first = false) {
  setForm(EXAMPLES[i]);
  sourceCode = null;
  showingExample = true;
  $("example-note").textContent = first
    ? "Đang hiển thị một tin ví dụ do nhóm soạn. Dán link tin đăng hoặc nhập thông tin phòng của bạn ở bên trái."
    : "Đang hiển thị tin ví dụ do nhóm soạn, không phải tin đăng thật.";
  $("example-note").hidden = false;
  baseline = null;
  predict();
}

function markOwn() {
  showingExample = false;
  $("example-note").hidden = true;
}

/* ============================================================ đọc link tin đăng */
async function importListing() {
  const url = $("url").value.trim();
  const status = $("import-status");
  if (!url) { status.textContent = "Dán link một tin cho thuê phòng vào ô trên."; status.className = "import-status error"; status.hidden = false; return; }
  status.textContent = "Đang đọc tin…"; status.className = "import-status"; status.hidden = false;
  $("fetch").disabled = true;
  try {
    const d = await api(`/api/fetch?url=${encodeURIComponent(url)}`);
    setForm({ ...d, asking: d.price ? Math.round(d.price * 10) / 10 : "" });
    sourceCode = d.source_code;
    const parts = [`Đã đọc tin từ ${d.source}`];
    if (d.price) parts.push(`giá đăng ${fmt1(d.price)} triệu`);
    if (!d.district) parts.push("chưa xác định được quận, hãy chọn tay");
    if (!d.size) parts.push("tin không ghi diện tích, hãy nhập tay");
    status.textContent = parts.join(" · ") + ".";
    markOwn(); baseline = null;
    await predict(true);
  } catch (err) {
    status.textContent = err.message; status.className = "import-status error";
  } finally {
    $("fetch").disabled = false;
  }
}

/* ============================================================ dự đoán */
const predictSoon = debounce(() => predict(), 300);

async function predict(record = false) {
  const size = parseFloat($("size").value);
  if (!(size >= 5 && size <= 150)) { showError("Diện tích cần nằm trong khoảng 5–150 m²."); return; }
  const q = {
    district: $("district").value, ward: $("ward").value || null, size,
    furnishing: furnishing || null, text: $("text").value,
    asking: $("asking").value ? parseFloat($("asking").value) : null,
    source: sourceCode,
  };
  $("error").hidden = true;
  $("result").classList.add("loading");
  try {
    const r = await api("/api/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(q) });
    if (baseline === null) baseline = r.price;
    render(r, q);
    if (record && !showingExample) remember(q, r);
  } catch (err) {
    showError(err.message);
  } finally {
    $("result").classList.remove("loading");
  }
}

function showError(msg) { $("error").textContent = msg; $("error").hidden = false; }

function render(r, q) {
  $("price").textContent = fmt(r.price);
  $("range").textContent = `${fmt(r.low)} – ${fmt(r.high)}`;
  // khoảng giá thích nghi: rộng khi loại tin / mức giá này khó đoán
  const width = ((r.high - r.low) / r.price) * 100;
  const note = $("range-note");
  note.hidden = !(width > WIDE || width < NARROW);
  note.textContent = width > WIDE
    ? "Khoảng giá rộng: những tin tương tự trong dữ liệu có giá dao động nhiều, nên khó định giá chắc chắn."
    : "Khoảng giá hẹp: những tin tương tự trong dữ liệu có giá khá ổn định.";

  const pill = $("type-pill");
  pill.textContent = r.listing_type.label;
  pill.classList.toggle("caution", r.listing_type.code !== "R");
  $("type-note").textContent = r.listing_type.note;
  $("type-note").hidden = r.listing_type.code === "R";

  const v = $("verdict");
  if (r.verdict) {
    const d = Math.abs(r.verdict.diff_pct);
    const ask = `Giá chủ trọ <strong>${fmt(q.asking)} triệu</strong>`;
    const copy = {
      high: ["Đắt hơn", `${ask} cao hơn ước tính ${d}% và vượt khoảng giá phổ biến. Nên thương lượng hoặc xem thêm tin khác.`],
      low: ["Rẻ hơn", `${ask} thấp hơn ước tính ${d}%. Giá tốt, nhưng nên kiểm tra kỹ phòng và các phí đi kèm (điện, nước, dịch vụ).`],
      fair: ["Hợp lý", `${ask} nằm trong khoảng giá phổ biến của các phòng tương tự.`],
    }[r.verdict.level];
    v.className = `verdict ${r.verdict.level}`;
    $("verdict-tag").textContent = copy[0];
    $("verdict-text").innerHTML = copy[1];
    v.hidden = false;
  } else {
    v.hidden = true;
  }

  const delta = baseline !== null && Math.abs(r.price - baseline) >= 0.01
    ? ` · so với lúc đầu ${r.price > baseline ? "+" : "−"}${fmt(Math.abs(r.price - baseline))} triệu` : "";
  $("chart-sub").textContent = r.area.n_similar
    ? `${r.area.n_similar} phòng riêng ở ${shortArea(r.area.name)} có diện tích gần ${q.size} m², giá trung vị ${fmt(r.area.median)} triệu${delta}`
    : `Chưa có phòng tương tự trong khu vực${delta}`;
  drawChart(r, q.asking, r.verdict?.level);
  drawWhy(r);
  drawWhatif(r);

  $("keywords").innerHTML = r.keywords.length
    ? `<span class="eyebrow" style="width: 100%">Đã nhận diện trong mô tả</span>` + r.keywords.map((k) => `<span class="chip">${esc(k)}</span>`).join("")
    : "";

  $("similar-area").textContent = `· ${shortArea(r.area.name)}, diện tích gần ${q.size} m²`;
  $("similar").innerHTML = r.similar.length ? r.similar.map((s) => `
    <tr>
      <td class="r num">${fmt(s.price)} tr</td>
      <td class="r num">${fmt1(s.size)} m²</td>
      <td class="area">${esc(shortArea(s.ward))}</td>
      <td class="title">${esc(s.title)}<small>${esc(s.source)}</small></td>
    </tr>`).join("") : `<tr><td colspan="4" style="color: var(--muted)">Chưa có tin tương tự trong khu vực này.</td></tr>`;
}

/* ============================================================ biểu đồ khoảng giá */
function niceStep(span) {
  return [0.25, 0.5, 1, 2, 5].find((s) => span / s <= 7) || 10;
}

function drawChart(r, asking, level) {
  const svg = $("chart");
  const W = 680, H = 150, padL = 10, padR = 10, axisY = 112, bandY = 46, bandH = 34;
  const prices = r.area.prices;
  const sorted = [...prices].sort((a, b) => a - b);
  const q = (p) => (sorted.length ? sorted[Math.floor(p * (sorted.length - 1))] : r.price);
  let lo = Math.min(r.low, q(0.03), asking || Infinity);
  let hi = Math.max(r.high, q(0.97), asking || -Infinity);
  const step = niceStep(hi - lo);
  lo = Math.max(0, Math.floor((lo - step * 0.3) / step) * step);
  hi = Math.ceil((hi + step * 0.3) / step) * step;
  const x = (val) => padL + ((val - lo) / (hi - lo)) * (W - padL - padR);

  let s = "";
  for (let t = lo; t <= hi + 1e-9; t += step) {
    s += `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${bandY - 16}" y2="${axisY}"/>`;
    s += `<text x="${x(t)}" y="${axisY + 18}" text-anchor="middle">${fmt1(t)}</text>`;
  }
  s += `<line class="axis" x1="${padL}" x2="${W - padR}" y1="${axisY}" y2="${axisY}"/>`;
  s += `<text x="${W - padR}" y="${axisY + 36}" text-anchor="end">triệu / tháng</text>`;
  s += `<rect class="band" x="${x(r.low)}" y="${bandY}" width="${Math.max(2, x(r.high) - x(r.low))}" height="${bandH}" rx="4"/>`;
  s += `<line class="est" x1="${x(r.price)}" x2="${x(r.price)}" y1="${bandY - 6}" y2="${bandY + bandH + 6}"/>`;
  s += `<text class="lbl-strong" x="${x(r.price)}" y="${bandY - 12}" text-anchor="middle">${fmt(r.price)}</text>`;
  const stripY = axisY - 14;
  prices.forEach((p, i) => {
    const jitter = ((i * 37) % 9) - 4;
    s += `<circle class="area-dot" cx="${x(p)}" cy="${stripY + jitter}" r="3" opacity="0.75"/>`;
    s += `<circle cx="${x(p)}" cy="${stripY + jitter}" r="8" fill="transparent" data-tip="${fmt(p)} triệu"/>`;
  });
  if (asking) {
    s += `<circle class="ask ${level || ""}" cx="${x(asking)}" cy="${bandY + bandH / 2}" r="7"/>`;
    s += `<circle cx="${x(asking)}" cy="${bandY + bandH / 2}" r="13" fill="transparent" data-tip="Giá chủ trọ: ${fmt(asking)} triệu"/>`;
  }
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = s;
  $("legend-ask").hidden = !asking;
  bindTips(svg, $("tooltip"), W);
}

function bindTips(svg, tip, W) {
  svg.querySelectorAll("[data-tip]").forEach((el) => {
    el.addEventListener("mouseenter", () => {
      const k = svg.getBoundingClientRect().width / W;
      tip.textContent = el.dataset.tip;
      tip.style.left = `${el.cx.baseVal.value * k}px`;
      tip.style.top = `${el.cy.baseVal.value * k}px`;
      tip.hidden = false;
    });
    el.addEventListener("mouseleave", () => { tip.hidden = true; });
  });
}

/* ============================================================ vì sao ra giá này */
function drawWhy(r) {
  const items = r.explain;
  const max = Math.max(10, ...items.map((d) => Math.abs(d.effect_pct)));
  $("why").innerHTML = items.length ? items.map((d) => {
    const w = (Math.abs(d.effect_pct) / max) * 50;
    return `<div class="why-row">
      <span class="why-label">${esc(d.label)}</span>
      <span class="why-track"><span class="why-bar ${d.effect_pct >= 0 ? "up" : "down"}" style="width: ${w}%"></span></span>
      <span class="why-val">${signed(d.effect_pct)}%</span>
    </div>`;
  }).join("") : `<p class="whatif-empty">Chưa đủ thông tin để giải thích.</p>`;
  $("why-note").textContent =
    `Tính trên phần tuyến tính của mô hình (chiếm ${r.explain_share}%). Đây là tương quan học từ tin đăng, không phải quan hệ nhân quả.`;
}

function drawWhatif(r) {
  $("whatif").innerHTML = r.whatif.length ? r.whatif.map((w) => `
    <button type="button" data-phrase="${esc(w.phrase)}">
      <span>+ ${esc(w.label)} <span style="color: var(--muted)">→ ${fmt(w.price)} triệu</span></span>
      <span class="plus ${w.delta_pct < 0 ? "neg" : ""}">${signed(w.delta_pct)}%</span>
    </button>`).join("") : `<p class="whatif-empty">Tin đã có đủ các tiện ích phổ biến.</p>`;
}

/* ============================================================ bản đồ */
const RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];
let map, mapData, wardLayer, tiles, metric = "ppm";

function isDark() {
  const t = document.documentElement.dataset.theme;
  return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}

// Nền bản đồ: Esri "World Gray Canvas" có sẵn bản sáng / tối, không cần khóa API. Một số mạng chặn máy chủ ô bản đồ
// của OSM (tile.openstreetmap.org), nên Esri được thử trước; lỗi liên tục thì chuyển sang nguồn kế tiếp, hết nguồn thì báo.
const OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const TILE_SOURCES = [
  { url: () => "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_"
             + (isDark() ? "Dark" : "Light") + "_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    opts: { maxZoom: 16, attribution: "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors" } },
  // ô OSM gốc nhiều màu: làm dịu / đảo màu ở chế độ tối bằng CSS (.osm-tiles trong style.css)
  { url: () => "https://tile.openstreetmap.org/{z}/{x}/{y}.png", osm: true, opts: { attribution: OSM_ATTR } },
];

function addTiles(i) {
  const src = TILE_SOURCES[i];
  const layer = L.tileLayer(src.url(), { maxZoom: 18, ...src.opts }).addTo(map);
  tiles = layer;
  $("map").classList.toggle("osm-tiles", Boolean(src.osm));
  let errors = 0, anyLoaded = false, gaveUp = false;
  layer.on("tileload", () => { anyLoaded = true; });
  layer.on("tileerror", () => {
    if (gaveUp || anyLoaded || ++errors <= 3) return;
    gaveUp = true;
    map.removeLayer(layer);
    if (i + 1 < TILE_SOURCES.length) addTiles(i + 1); else $("map-offline").hidden = false;
  });
}

async function initMap() {
  if (loaded.map) { map.invalidateSize(); return; }
  loaded.map = true;
  mapData = await api("/api/map");
  map = L.map("map", { zoomControl: true, scrollWheelZoom: true }).setView([21.02, 105.82], 12);
  addTiles(0);
  wardLayer = L.layerGroup().addTo(map);
  drawWards();
  $("map-metric").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    metric = b.dataset.metric;
    document.querySelectorAll("#map-metric button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    drawWards();
  });
  drawRank();
  const bounds = L.latLngBounds(mapData.wards.filter((w) => w.n >= 15).map((w) => [w.lat, w.lon]));
  if (bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20] });
}

function drawWards() {
  const vals = mapData.wards.map((w) => w[metric]).sort((a, b) => a - b);
  const qs = RAMP.slice(1).map((_, i) => vals[Math.floor(((i + 1) / RAMP.length) * (vals.length - 1))]);
  const color = (v) => RAMP[qs.filter((t) => v > t).length];
  wardLayer.clearLayers();
  const unit = metric === "ppm" ? "nghìn/m²" : "triệu";
  mapData.wards.forEach((w) => {
    L.circleMarker([w.lat, w.lon], {
      radius: 5 + Math.sqrt(w.n) * 0.9, color: isDark() ? "#0e1116" : "#ffffff", weight: 1.5,
      fillColor: color(w[metric]), fillOpacity: 0.88,
    }).bindPopup(`<div class="pop-title">${esc(w.ward)}</div><div class="pop-sub">${esc(w.district)} · ${w.n} tin phòng riêng</div>
      <div class="pop-grid"><span>Giá trung vị</span><b>${fmt(w.price)} triệu</b><span>Giá / m²</span><b>${nf0.format(w.ppm)} nghìn</b>
      <span>Diện tích TV</span><b>${fmt1(w.size)} m²</b></div>`)
      .bindTooltip(`${shortArea(w.ward)}: ${metric === "ppm" ? nf0.format(w.ppm) : fmt(w.price)} ${unit}`)
      .addTo(wardLayer);
  });
  $("ramp-bar").innerHTML = RAMP.map((c) => `<i style="background: ${c}"></i>`).join("");
  const f = (v) => (metric === "ppm" ? nf0.format(v) : fmt1(v));
  $("ramp-ticks").innerHTML = `<span>${f(vals[0])}</span><span>${f(vals[Math.floor(vals.length / 2)])}</span><span>${f(vals[vals.length - 1])} ${unit}</span>`;
}

function drawRank() {
  const ds = mapData.districts;
  const max = Math.max(...ds.map((d) => d.price));
  $("rank").innerHTML = ds.map((d) => `
    <div class="rank-row" title="${d.n} tin · ${nf0.format(d.ppm)} nghìn/m²">
      <span>${esc(d.district)}</span>
      <span><div class="rank-bar" style="width: ${(d.price / max) * 100}%"></div></span>
      <span class="rank-val">${fmt1(d.price)}</span>
    </div>`).join("");
}

/* ============================================================ về mô hình */
async function initAbout() {
  if (loaded.about) return;
  loaded.about = true;
  const a = await api("/api/about");
  const best = a.models.reduce((m, r) => (!r.model.includes("rò rỉ") && r["MAE (triệu)"] < m["MAE (triệu)"] ? r : m), a.models[0]);
  const tempBest = a.temporal.find((t) => t["mô hình"] === best.model && t["tập test"] === "tất cả tin mới");
  $("stats").innerHTML = [
    [a.data.total.toLocaleString("vi-VN"), "tin đăng sau làm sạch"],
    [a.data.private.toLocaleString("vi-VN"), "tin phòng riêng dùng để huấn luyện"],
    [`${fmt(best["MAE (triệu)"])} tr`, "sai số trung bình (MAE)"],
    [`${fmt1(best["MAPE (%)"])}%`, "sai số tương đối (MAPE)"],
    tempBest ? [`${fmt1(tempBest["MAPE (%)"])}%`, `MAPE trên ${tempBest["số tin"]} tin đăng mới`] : null,
  ].filter(Boolean).map(([b, s]) => `<div class="stat"><b>${b}</b><span>${s}</span></div>`).join("");

  const models = a.models.filter((m) => !m.model.startsWith("Dummy"));
  const dummy = a.models.find((m) => m.model.startsWith("Dummy"));
  const maxMae = Math.max(...a.models.map((m) => m["MAE (triệu)"]));
  const rows = (dummy ? [dummy] : []).concat(models);
  $("models").innerHTML = rows.map((m) => {
    const leak = m.model.includes("rò rỉ");
    const name = leak ? "Mô hình tốt nhất, chia ngẫu nhiên" : m.model.replace("Dummy (trung bình)", "Đoán bằng giá trung bình");
    return `<div class="hbar ${m === best ? "best" : ""} ${leak ? "leak" : ""}">
      <span class="hbar-name">${esc(name)}</span>
      <span class="hbar-track"><div class="hbar-fill" style="width: ${(m["MAE (triệu)"] / maxMae) * 100}%"></div></span>
      <span class="hbar-val">${fmt(m["MAE (triệu)"])}</span></div>`;
  }).join("");

  const maxR2 = Math.max(...a.ablation.map((d) => d.r2));
  $("ablation").innerHTML = a.ablation.map((d, i) => `<div class="hbar ${i === 0 ? "best" : ""}">
      <span class="hbar-name">${esc(d.config.replace(/^bỏ /, "Bỏ "))}</span>
      <span class="hbar-track"><div class="hbar-fill" style="width: ${(d.r2 / maxR2) * 100}%"></div></span>
      <span class="hbar-val">${fmt(d.r2)}</span></div>`).join("");

  const keepGroups = ["tất cả", "giá dự đoán < 2,5 triệu", "giá dự đoán > 5 triệu", "nguồn mogi", "giá thật < 2 triệu", "giá thật > 5 triệu"];
  const keepMethods = ["một độ rộng chung", "thích nghi + theo mức giá dự đoán"];
  const groupLabel = (g) => g.replace("nguồn mogi", "nguồn Mogi");
  const iv = (a.intervals || []).filter((r) => keepGroups.includes(r["nhóm tin"]) && keepMethods.includes(r["cách tính"]));
  $("intervals").innerHTML = iv.length ? `<thead><tr><th>Nhóm tin</th><th>Cách tính</th><th class="r">Độ phủ</th><th class="r">Độ rộng</th></tr></thead><tbody>` +
    iv.map((r) => `<tr><td>${esc(groupLabel(r["nhóm tin"]))}</td><td>${esc(r["cách tính"])}</td>
      <td class="r num">${fmt1(r["độ phủ (%)"])}%</td><td class="r num">${fmt(r["độ rộng TB (triệu)"])} tr</td></tr>`).join("") + "</tbody>"
    : `<tbody><tr><td style="color: var(--muted)">Chạy src/intervals.py để có số liệu.</td></tr></tbody>`;

  const t = a.temporal.filter((r) => !r["mô hình"].startsWith("Dummy"));
  $("temporal").innerHTML = `<thead><tr><th>Mô hình</th><th>Tập test</th><th class="r">Số tin</th><th class="r">MAE</th><th class="r">MAPE</th></tr></thead><tbody>` +
    t.map((r) => `<tr><td>${esc(r["mô hình"])}</td><td>${esc(r["tập test"])}</td><td class="r num">${r["số tin"]}</td>
      <td class="r num">${fmt(r["MAE (triệu)"])}</td><td class="r num">${fmt1(r["MAPE (%)"])}%</td></tr>`).join("") + "</tbody>";
}

init().catch((err) => showError(`Không kết nối được máy chủ: ${err.message}`));
