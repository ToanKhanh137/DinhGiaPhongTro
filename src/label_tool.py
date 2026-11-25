r"""TRANG GÁN NHÃN cho người gán thứ hai (đo độ đồng thuận, xem src/label_agreement.py).

Mở một trang web cục bộ, hiện từng tin trong data/labels/kappa_sample_100.csv (không kèm nhãn cũ). Bấm phím R / G / N để
gán; nhãn được ghi ngay vào file CSV nên có thể dừng giữa chừng rồi mở lại gán tiếp.

    python src/label_tool.py            # mở http://127.0.0.1:8010
    python src/label_agreement.py       # sau khi gán đủ 100 tin: tính Cohen's kappa
"""
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pandas as pd

from label_agreement import CLASSES, SAMPLE_FILE

HOST, PORT = "127.0.0.1", 8010
LOCK = threading.Lock()


def load():
    df = pd.read_csv(SAMPLE_FILE, dtype={"label": "string", "labeled_by": "string"})
    df["label"] = df["label"].fillna("").str.strip().str.upper()
    df["labeled_by"] = df["labeled_by"].fillna("")
    return df


def save_label(item_id, label, name):
    with LOCK:
        df = load()
        hit = df["id"] == item_id
        if not hit.any():
            raise KeyError(item_id)
        df.loc[hit, "label"] = label
        df.loc[hit, "labeled_by"] = name if label else ""
        df.to_csv(SAMPLE_FILE, index=False, encoding="utf-8-sig")
        return int((df["label"] != "").sum())


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, content_type="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self.reply(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/items":
            df = load()
            items = [{"id": r.id, "price": None if pd.isna(r.price) else float(r.price),
                      "size": None if pd.isna(r.size) else float(r.size), "text": r.text, "label": r.label}
                     for r in df.itertuples()]
            names = [n for n in df["labeled_by"].unique() if n]
            self.reply(200, {"items": items, "name": names[0] if names else ""})
        else:
            self.reply(404, {"error": "không có trang này"})

    def do_POST(self):
        if self.path != "/api/label":
            return self.reply(404, {"error": "không có trang này"})
        try:
            q = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            label, name = str(q.get("label", "")).upper(), str(q.get("name", "")).strip()
            if label not in CLASSES + [""]:
                return self.reply(400, {"error": "nhãn chỉ nhận R, G, N"})
            if label and not name:
                return self.reply(400, {"error": "chưa nhập họ tên người gán"})
            self.reply(200, {"done": save_label(q["id"], label, name)})
        except KeyError:
            self.reply(400, {"error": "không tìm thấy tin"})
        except PermissionError:
            self.reply(500, {"error": "không ghi được file CSV (đang mở bằng Excel?). Đóng Excel rồi gán lại tin này."})

    def log_message(self, *args):  # không in từng request ra màn hình
        pass


PAGE = r"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gán nhãn loại tin</title>
<style>
  :root { --paper: #f1f3f6; --surface: #fff; --ink: #121722; --ink-2: #485165; --muted: #7a8394; --line: #dfe3ea;
          --accent: #1d4f94; --accent-soft: #e4ecf8; --warn: #c0352b; --good: #1e8a4a; --mark: #fff1b8; }
  @media (prefers-color-scheme: dark) {
    :root { --paper: #0e1116; --surface: #161b23; --ink: #e8ecf2; --ink-2: #aeb6c4; --muted: #7d8697; --line: #262d39;
            --accent: #79abee; --accent-soft: #1a2638; --warn: #f0705f; --good: #43bf72; --mark: #4a3f12; color-scheme: dark; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--paper); color: var(--ink); font: 16px/1.55 "Segoe UI", Roboto, Arial, sans-serif; }
  main { max-width: 1080px; margin: 0 auto; padding: 20px 16px 48px; display: grid; gap: 16px; grid-template-columns: minmax(0, 1fr) 320px; }
  @media (max-width: 860px) { main { grid-template-columns: minmax(0, 1fr); } }
  header { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: center; }
  h1 { font-size: 20px; margin: 0; flex: 1 1 auto; }
  .name { display: flex; gap: 8px; align-items: center; color: var(--ink-2); font-size: 14px; }
  .name input { font: inherit; padding: 6px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface);
                color: var(--ink); width: 210px; }
  .name input.need { border-color: var(--warn); }
  .card { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px; }
  .bar { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; margin: 8px 0 14px; }
  .bar div { height: 100%; background: var(--accent); width: 0; }
  .meta { display: flex; flex-wrap: wrap; gap: 6px 18px; color: var(--ink-2); font-size: 14px; }
  .meta b { color: var(--ink); font-variant-numeric: tabular-nums; }
  .facts { display: flex; flex-wrap: wrap; gap: 8px 24px; margin: 4px 0 12px; font-size: 15px; }
  .facts b { font-size: 18px; font-variant-numeric: tabular-nums; }
  .text { white-space: pre-wrap; overflow-wrap: anywhere; border-top: 1px solid var(--line); padding-top: 12px; max-height: 52vh; overflow: auto; }
  mark { background: var(--mark); color: inherit; padding: 0 2px; border-radius: 3px; }
  .choices { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 16px; }
  button { font: inherit; cursor: pointer; border: 1px solid var(--line); background: var(--surface); color: var(--ink);
           border-radius: 8px; padding: 10px 12px; text-align: left; }
  button:hover { border-color: var(--accent); }
  button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .choices button b { display: block; font-size: 17px; }
  .choices button span { color: var(--ink-2); font-size: 13px; }
  .choices button.on { background: var(--accent-soft); border-color: var(--accent); }
  .nav { display: flex; gap: 10px; margin-top: 12px; align-items: center; color: var(--muted); font-size: 13px; }
  .nav button { padding: 6px 12px; }
  .msg { min-height: 22px; margin-top: 10px; font-size: 14px; color: var(--warn); }
  .msg.ok { color: var(--good); }
  aside h2 { font-size: 15px; margin: 0 0 8px; }
  aside p, aside li { font-size: 14px; color: var(--ink-2); margin: 0 0 8px; }
  aside ol, aside ul { padding-left: 18px; margin: 0 0 12px; }
  aside b { color: var(--ink); }
  kbd { font: 12px/1 Consolas, monospace; border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 4px; padding: 2px 5px;
        background: var(--paper); color: var(--ink); }
</style>
</head>
<body>
<main>
  <header>
    <h1>Gán nhãn loại tin đăng</h1>
    <label class="name">Họ tên người gán <input id="name" autocomplete="off" placeholder="nhập trước khi gán"></label>
  </header>

  <section class="card">
    <div class="meta"><span>Tin <b id="pos">–</b></span><span>Đã gán <b id="done">–</b></span><span id="idline"></span></div>
    <div class="bar"><div id="bar"></div></div>
    <div class="facts"><span>Giá đăng <b id="price">–</b></span><span>Diện tích <b id="size">–</b></span></div>
    <div class="text" id="text"></div>
    <div class="choices">
      <button data-label="R"><b>R · phòng riêng</b><span>giá của một phòng cụ thể</span></button>
      <button data-label="G"><b>G · ở ghép</b><span>giá theo người / giường / slot</span></button>
      <button data-label="N"><b>N · nhiều mức giá</b><span>nhiều phòng khác giá, khoảng giá, giá "từ"</span></button>
    </div>
    <div class="nav">
      <button id="prev">← Tin trước</button><button id="next">Tin sau →</button><button id="todo">Tới tin chưa gán</button>
      <span>Phím: <kbd>R</kbd> <kbd>G</kbd> <kbd>N</kbd> gán và sang tin sau · <kbd>←</kbd> <kbd>→</kbd> chuyển tin</span>
    </div>
    <div class="msg" id="msg"></div>
  </section>

  <aside class="card">
    <h2>Câu hỏi khi gán</h2>
    <p><b>Con số giá của tin này là giá của cái gì?</b></p>
    <h2>Thứ tự ưu tiên</h2>
    <ol>
      <li>Giá chính là giá theo <b>người / giường</b> → <b>G</b>.</li>
      <li>Không phải G, và có <b>từ 2 mức giá phòng khác nhau</b>, hoặc <b>khoảng giá / giá "từ"</b> → <b>N</b>.</li>
      <li>Còn lại → <b>R</b>.</li>
    </ol>
    <h2>Trường hợp ranh giới</h2>
    <ul>
      <li>Một phòng, giá đổi theo số người ở hoặc thời hạn hợp đồng / ưu đãi → <b>R</b></li>
      <li>Nhiều phòng cùng một giá → <b>R</b></li>
      <li>Giá tính cả phòng, có nhắc "có thể ở ghép" → <b>R</b></li>
      <li>Hai phòng hai giá, kể cả khi giá đăng khớp một trong hai → <b>N</b></li>
      <li>Một phòng nhưng chỉ ghi khoảng ("2tr – 2tr2") → <b>N</b></li>
      <li>Tòa nhà nhiều loại phòng, mô tả không ghi giá → <b>N</b></li>
      <li>Nhiều phòng, mô tả không ghi giá nào → <b>R</b></li>
      <li>Giá trong mô tả lệch giá đăng, chỉ có một phòng → <b>R</b></li>
      <li>Điện, nước, dịch vụ, cọc, phí môi giới: bỏ qua</li>
    </ul>
    <p>Đầy đủ: <code>docs/HUONG_DAN_GAN_NHAN.md</code>. Chữ tô vàng là số tiền và từ khóa ở ghép, chỉ để dễ đọc.</p>
  </aside>
</main>

<script>
const $ = (id) => document.getElementById(id);
let items = [], cur = 0;
const MONEY = /(\d[\d.,]*\s*(?:triệu|tr\d*|củ|k|nghìn|ngàn|đ|vnd|vnđ)(?![a-zà-ỹ])|ở ghép|o ghep|\/\s*(?:1\s*)?(?:người|ng|nguoi|bạn|giường|slot)(?![a-zà-ỹ])|giường tầng|sleepbox|dorm|ktx|ký túc|slot|giá từ|chỉ từ|từ \d)/gi;

function esc(s) { return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }
function money(v) { return v == null ? "không rõ" : (v / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 2 }) + " triệu"; }

function show() {
  const it = items[cur], done = items.filter((x) => x.label).length;
  $("pos").textContent = (cur + 1) + " / " + items.length;
  $("done").textContent = done + " / " + items.length;
  $("bar").style.width = (done / items.length * 100) + "%";
  $("idline").textContent = "Mã tin " + it.id;
  $("price").textContent = money(it.price);
  $("size").textContent = it.size == null ? "không ghi" : it.size.toLocaleString("vi-VN") + " m²";
  $("text").innerHTML = esc(it.text || "").replace(MONEY, "<mark>$&</mark>");
  $("text").scrollTop = 0;
  document.querySelectorAll(".choices button").forEach((b) => b.classList.toggle("on", b.dataset.label === it.label));
  if (done === items.length) say("Đã gán đủ " + items.length + " tin. Đóng trang này rồi chạy: python src/label_agreement.py", true);
}

function say(text, ok) { $("msg").textContent = text; $("msg").classList.toggle("ok", Boolean(ok)); }

function go(i) { cur = Math.max(0, Math.min(items.length - 1, i)); say(""); show(); }

function nextTodo() {
  for (let k = 1; k <= items.length; k++) { const i = (cur + k) % items.length; if (!items[i].label) return go(i); }
  show();
}

async function label(value) {
  const name = $("name").value.trim();
  $("name").classList.toggle("need", !name);
  if (!name) { say("Nhập họ tên người gán ở góc trên trước khi gán."); $("name").focus(); return; }
  const it = items[cur];
  try {
    const res = await fetch("/api/label", { method: "POST", headers: { "Content-Type": "application/json" },
                                            body: JSON.stringify({ id: it.id, label: value, name }) });
    const data = await res.json();
    if (!res.ok) { say(data.error || "Không lưu được nhãn."); return; }
    it.label = value;
    if (cur < items.length - 1 && items.some((x) => !x.label)) go(cur + 1); else show();
  } catch (e) { say("Mất kết nối với chương trình gán nhãn. Kiểm tra cửa sổ đang chạy python src/label_tool.py."); }
}

document.querySelectorAll(".choices button").forEach((b) => b.addEventListener("click", () => label(b.dataset.label)));
$("prev").addEventListener("click", () => go(cur - 1));
$("next").addEventListener("click", () => go(cur + 1));
$("todo").addEventListener("click", nextTodo);
document.addEventListener("keydown", (e) => {
  if (e.target === $("name") || e.ctrlKey || e.altKey || e.metaKey) return;
  const k = e.key.toLowerCase();
  if (k === "r" || k === "g" || k === "n") { e.preventDefault(); label(k.toUpperCase()); }
  else if (e.key === "ArrowLeft") go(cur - 1);
  else if (e.key === "ArrowRight") go(cur + 1);
});

fetch("/api/items").then((r) => r.json()).then((d) => {
  items = d.items;
  $("name").value = d.name || "";
  const first = items.findIndex((x) => !x.label);
  go(first < 0 ? 0 : first);
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    if not SAMPLE_FILE.exists():
        raise SystemExit(f"Chưa có {SAMPLE_FILE}. Chạy: python src/label_agreement.py --make")
    url = f"http://{HOST}:{PORT}"
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Trang gán nhãn: {url}  (Ctrl+C để dừng; nhãn được ghi ngay vào {SAMPLE_FILE.name})", flush=True)
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Đã dừng.")
