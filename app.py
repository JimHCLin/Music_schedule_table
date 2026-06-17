import sqlite3
from flask import Flask, request, redirect, session

app = Flask(__name__)

# --- 🔒 安全設定 ---
app.secret_key = "x7#m9Z!qP2@sK5wE8$vR"
ADMIN_PASSWORD = "0802"

DB_FILE = "schedule.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                day TEXT,
                slot TEXT,
                student_name TEXT,
                PRIMARY KEY (day, slot)
            )
        """)
init_db()

DAYS = ["週一", "週二", "週三", "週四", "週五"]
SLOTS = ["第一堂", "第二堂", "第三堂", "第四堂", "第五堂", "第六堂", "第七堂", "第八堂"]

def get_all_bookings():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT day, slot, student_name FROM bookings")
        rows = cursor.fetchall()
    return {(r[0], r[1]): r[2] for r in rows}

SHARED_STYLES = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Noto+Serif+TC:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --ink:     #0D0C0A;
    --parchment: #F5EDD6;
    --gold:    #C9A84C;
    --gold-dim: #8a6e2f;
    --velvet:  #8B1A1A;
    --midnight:#2A3A5E;
    --smoke:   #3a3530;
    --mist:    #b5a98a;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Noto Serif TC', serif;
    background-color: var(--ink);
    color: var(--parchment);
    min-height: 100vh;
  }

  /* ── 五線譜背景紋路 ── */
  .staff-bg {
    background-color: var(--ink);
    background-image:
      repeating-linear-gradient(
        to bottom,
        transparent 0px,
        transparent 22px,
        rgba(180,160,100,0.10) 22px,
        rgba(180,160,100,0.10) 23px
      );
    background-size: 100% 115px;
  }

  /* ── 頁面容器 ── */
  .page-wrap {
    max-width: 960px;
    margin: 0 auto;
    padding: 2.5rem 1.5rem;
  }

  /* ── 標題區 ── */
  .site-header { text-align: center; margin-bottom: 2.5rem; }

  .site-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(1.8rem, 5vw, 3rem);
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--gold);
    line-height: 1.15;
    text-shadow: 0 2px 24px rgba(201,168,76,0.25);
  }

  .site-title em {
    font-style: italic;
    font-weight: 400;
    color: var(--parchment);
    opacity: 0.7;
    font-size: 0.6em;
    display: block;
    letter-spacing: 0.25em;
    margin-top: 0.4rem;
  }

  .staff-divider {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 1.2rem auto;
    max-width: 380px;
    opacity: 0.5;
  }
  .staff-divider::before, .staff-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--gold);
  }
  .staff-divider span { font-size: 1.1rem; color: var(--gold); }

  .site-sub {
    font-size: 0.72rem;
    letter-spacing: 0.3em;
    color: var(--mist);
    text-transform: uppercase;
  }
  .site-sub strong { color: var(--gold); }

  /* ── 通知訊息 ── */
  .alert {
    border-radius: 6px;
    padding: 0.75rem 1.2rem;
    margin-bottom: 1.5rem;
    font-size: 0.82rem;
    text-align: center;
    letter-spacing: 0.04em;
    border-left: 3px solid;
  }
  .alert-error  { background: rgba(139,26,26,0.2);  border-color: var(--velvet); color: #f4a0a0; }
  .alert-success{ background: rgba(42,58,94,0.3);   border-color: var(--midnight); color: #a0bff4; }

  /* ── 課表 ── */
  .table-wrap {
    overflow-x: auto;
    border-radius: 10px;
    border: 1px solid rgba(201,168,76,0.2);
    box-shadow: 0 4px 40px rgba(0,0,0,0.6);
  }

  table { width: 100%; border-collapse: collapse; }

  thead tr {
    background: rgba(13,12,10,0.9);
    border-bottom: 2px solid rgba(201,168,76,0.35);
  }

  thead th {
    padding: 0.9rem 0.6rem;
    font-family: 'Playfair Display', serif;
    font-size: 0.8rem;
    letter-spacing: 0.2em;
    color: var(--gold);
    font-weight: 700;
    text-align: center;
  }

  tbody tr {
    border-bottom: 1px solid rgba(201,168,76,0.08);
    transition: background 0.18s;
  }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover { background: rgba(201,168,76,0.04); }

  td {
    padding: 0.7rem 0.5rem;
    text-align: center;
    vertical-align: middle;
    border-right: 1px solid rgba(201,168,76,0.06);
    font-size: 0.78rem;
  }
  td:last-child { border-right: none; }

  .slot-label {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    color: var(--gold-dim);
    font-size: 0.8rem;
    background: rgba(13,12,10,0.6);
    min-width: 72px;
  }

  /* 已被預約 */
  .booked-cell {
    background: rgba(139,26,26,0.12);
    color: #e8a0a0;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
  }
  .booked-cell .note-icon { opacity: 0.6; margin-right: 3px; }

  /* 空格輸入 */
  .book-form { display: flex; gap: 5px; justify-content: center; align-items: center; }

  .book-input {
    background: rgba(245,237,214,0.05);
    border: 1px solid rgba(201,168,76,0.25);
    border-radius: 4px;
    padding: 0.3rem 0.5rem;
    font-size: 0.72rem;
    font-family: 'Noto Serif TC', serif;
    color: var(--parchment);
    width: 80px;
    text-align: center;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .book-input::placeholder { color: rgba(181,169,138,0.4); }
  .book-input:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 2px rgba(201,168,76,0.15);
  }

  .book-btn {
    background: none;
    border: 1px solid rgba(201,168,76,0.4);
    color: var(--gold);
    font-size: 0.68rem;
    font-family: 'Noto Serif TC', serif;
    letter-spacing: 0.08em;
    padding: 0.3rem 0.55rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.18s, color 0.18s, transform 0.1s;
  }
  .book-btn:hover { background: rgba(201,168,76,0.15); color: #f0d590; }
  .book-btn:active { transform: scale(0.95); }

  /* ── 頁尾 ── */
  .page-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1.8rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(201,168,76,0.1);
    font-size: 0.72rem;
    color: var(--mist);
    letter-spacing: 0.1em;
  }
  .page-footer a {
    color: var(--gold-dim);
    text-decoration: none;
    transition: color 0.2s;
  }
  .page-footer a:hover { color: var(--gold); }

  /* ── 登入頁 ── */
  .login-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 2rem;
  }
  .login-card {
    background: rgba(20,18,14,0.85);
    border: 1px solid rgba(201,168,76,0.22);
    border-radius: 14px;
    padding: 2.5rem 2rem;
    width: 100%;
    max-width: 360px;
    text-align: center;
    box-shadow: 0 8px 60px rgba(0,0,0,0.7);
    backdrop-filter: blur(8px);
  }
  .login-icon {
    font-size: 2.4rem;
    margin-bottom: 1rem;
    display: block;
    opacity: 0.85;
  }
  .login-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    color: var(--gold);
    letter-spacing: 0.12em;
    margin-bottom: 0.2rem;
  }
  .login-sub {
    font-size: 0.65rem;
    letter-spacing: 0.3em;
    color: var(--mist);
    text-transform: uppercase;
    margin-bottom: 1.8rem;
  }
  .login-label {
    display: block;
    text-align: left;
    font-size: 0.7rem;
    letter-spacing: 0.15em;
    color: var(--mist);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
  }
  .login-input {
    width: 100%;
    background: rgba(245,237,214,0.04);
    border: 1px solid rgba(201,168,76,0.25);
    border-radius: 6px;
    padding: 0.7rem 1rem;
    font-size: 0.88rem;
    font-family: 'Noto Serif TC', serif;
    color: var(--parchment);
    text-align: center;
    letter-spacing: 0.2em;
    outline: none;
    transition: border-color 0.2s;
    margin-bottom: 1.2rem;
  }
  .login-input:focus { border-color: var(--gold); }
  .login-btn {
    width: 100%;
    background: linear-gradient(135deg, #b8922a 0%, #d4a84b 50%, #b8922a 100%);
    color: var(--ink);
    font-family: 'Playfair Display', serif;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    padding: 0.75rem;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
  }
  .login-btn:hover { opacity: 0.9; }
  .login-btn:active { transform: scale(0.98); }
  .login-back {
    display: block;
    margin-top: 1.4rem;
    font-size: 0.7rem;
    color: var(--mist);
    text-decoration: none;
    letter-spacing: 0.1em;
    transition: color 0.2s;
  }
  .login-back:hover { color: var(--gold); }

  /* ── 後台頁 ── */
  .admin-wrap { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }
  .admin-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid rgba(201,168,76,0.2);
    flex-wrap: wrap;
    gap: 0.8rem;
  }
  .admin-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    color: var(--gold);
    letter-spacing: 0.1em;
  }
  .admin-sub { font-size: 0.68rem; color: var(--mist); margin-top: 0.2rem; letter-spacing: 0.15em; }
  .admin-links { display: flex; gap: 1.2rem; font-size: 0.72rem; }
  .admin-links a { color: var(--mist); text-decoration: none; letter-spacing: 0.1em; transition: color 0.2s; }
  .admin-links a:hover { color: var(--gold); }
  .admin-links a.danger:hover { color: #f4a0a0; }

  .admin-grid { display: grid; grid-template-columns: 1fr 280px; gap: 1.5rem; align-items: start; }
  @media(max-width:700px){ .admin-grid { grid-template-columns: 1fr; } }

  .card {
    background: rgba(20,18,14,0.7);
    border: 1px solid rgba(201,168,76,0.15);
    border-radius: 10px;
    overflow: hidden;
  }
  .card-head {
    padding: 0.8rem 1.2rem;
    background: rgba(13,12,10,0.8);
    border-bottom: 1px solid rgba(201,168,76,0.15);
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    color: var(--mist);
    text-transform: uppercase;
  }

  .admin-table { width: 100%; border-collapse: collapse; }
  .admin-table th {
    padding: 0.7rem 1rem;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mist);
    border-bottom: 1px solid rgba(201,168,76,0.12);
    text-align: left;
  }
  .admin-table td {
    padding: 0.7rem 1rem;
    font-size: 0.8rem;
    border-bottom: 1px solid rgba(201,168,76,0.06);
    color: var(--parchment);
    text-align: left;
  }
  .admin-table tr:last-child td { border-bottom: none; }
  .admin-table tr:hover td { background: rgba(201,168,76,0.03); }

  .del-btn {
    background: none;
    border: 1px solid rgba(139,26,26,0.5);
    color: #d08080;
    font-size: 0.68rem;
    font-family: 'Noto Serif TC', serif;
    letter-spacing: 0.08em;
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.18s, color 0.18s;
  }
  .del-btn:hover { background: rgba(139,26,26,0.2); color: #f4a0a0; }

  .empty-note {
    text-align: center;
    padding: 2.5rem;
    color: var(--mist);
    font-size: 0.78rem;
    letter-spacing: 0.12em;
    font-style: italic;
  }
</style>
"""

# --- 前端：課表主頁 ---
@app.route("/")
def index_page():
    error = request.args.get("error", "")
    success = request.args.get("success", "")
    bookings = get_all_bookings()

    table_rows = ""
    for slot in SLOTS:
        table_rows += f"<tr>"
        table_rows += f"<td class='slot-label'>{slot}</td>"
        for day in DAYS:
            name = bookings.get((day, slot), "")
            if name:
                table_rows += f"<td class='booked-cell'><span class='note-icon'>♩</span>{name}</td>"
            else:
                table_rows += f"""
                <td>
                  <form action='/book' method='post' class='book-form'>
                    <input type='hidden' name='day' value='{day}'>
                    <input type='hidden' name='slot' value='{slot}'>
                    <input type='text' name='name' placeholder='姓名' required class='book-input'>
                    <button type='submit' class='book-btn'>預約</button>
                  </form>
                </td>
                """
        table_rows += "</tr>"

    alert_html = ""
    if error:
        alert_html = f"<div class='alert alert-error'>⚠ {error}</div>"
    elif success:
        alert_html = f"<div class='alert alert-success'>✦ {success}</div>"

    day_headers = "".join(f"<th>{d}</th>" for d in DAYS)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <title>樂章共鳴 · 時段預約</title>
  {SHARED_STYLES}
</head>
<body class="staff-bg">
  <div class="page-wrap">

    <header class="site-header">
      <h1 class="site-title">
        樂章共鳴
        <em>Harmonia · 時段預約系統</em>
      </h1>
      <div class="staff-divider"><span>𝄞</span></div>
      <p class="site-sub">尋找你的專屬節奏 &middot; 每人上限演繹 <strong>5</strong> 個時段</p>
    </header>

    {alert_html}

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="min-width:72px">時段</th>
            {day_headers}
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
    </div>

    <footer class="page-footer">
      <span>🎻 琴房容納上限：10 人</span>
      <a href="/admin">指揮台後台 →</a>
    </footer>

  </div>
</body>
</html>"""

# --- 登記邏輯 ---
@app.route("/book", methods=["POST"])
def book_slot():
    day = request.form.get("day")
    slot = request.form.get("slot")
    name = request.form.get("name", "").strip()

    if not name:
        return redirect("/?error=名字不能為空！")

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bookings WHERE student_name = ?", (name,))
        count = cursor.fetchone()[0]
        if count >= 5:
            return redirect("/?error=已達 5 個時段演繹上限。")
        try:
            cursor.execute("INSERT INTO bookings (day, slot, student_name) VALUES (?, ?, ?)", (day, slot, name))
            conn.commit()
        except sqlite3.IntegrityError:
            return redirect("/?error=此時段已被其他演出者捷足先登。")

    return redirect(f"/?success=【{name}】已成功預約 {day} {slot}。")

# --- 後台登入 ---
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error_msg = ""
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect("/admin")
        else:
            error_msg = "<div class='alert alert-error' style='margin-bottom:1rem'>✕ 密鑰不符，無法開啟指揮門</div>"

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <title>指揮台 · 登入</title>
  {SHARED_STYLES}
</head>
<body class="staff-bg">
  <div class="login-wrap">
    <div class="login-card">
      <span class="login-icon">𝄢</span>
      <h2 class="login-title">後台指揮室</h2>
      <p class="login-sub">Conductor Control Room</p>
      {error_msg}
      <form method="post">
        <label class="login-label">輸入指揮密鑰</label>
        <input type="password" name="password" required class="login-input" placeholder="· · · ·">
        <button type="submit" class="login-btn">解鎖控制台</button>
      </form>
      <a href="/" class="login-back">← 返回前台樂章</a>
    </div>
  </div>
</body>
</html>"""

# --- 後台管理 ---
@app.route("/admin")
def admin_page():
    if not session.get("is_admin"):
        return redirect("/admin/login")

    bookings = get_all_bookings()
    student_counts = {}
    for name in bookings.values():
        student_counts[name] = student_counts.get(name, 0) + 1

    admin_rows = ""
    for day in DAYS:
        for slot in SLOTS:
            name = bookings.get((day, slot), "")
            if name:
                admin_rows += f"""
                <tr>
                  <td style="color:var(--gold-dim)">{day}</td>
                  <td>{slot}</td>
                  <td style="color:#e8a0a0">♩ {name}</td>
                  <td>
                    <form action='/admin/delete' method='post'>
                      <input type='hidden' name='day' value='{day}'>
                      <input type='hidden' name='slot' value='{slot}'>
                      <button type='submit' class='del-btn'>取消預約</button>
                    </form>
                  </td>
                </tr>"""

    summary_rows = "".join(
        f"<tr><td>{s}</td><td style='text-align:center;color:var(--gold);font-weight:600'>{c} / 5</td></tr>"
        for s, c in student_counts.items()
    )

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <title>指揮台管理中心</title>
  {SHARED_STYLES}
</head>
<body class="staff-bg">
  <div class="admin-wrap">

    <div class="admin-header">
      <div>
        <div class="admin-title">🎻 指揮台管理中心</div>
        <div class="admin-sub">Conductor Dashboard · 預約節目清單</div>
      </div>
      <div class="admin-links">
        <a href="/">← 前台課表</a>
        <a href="/admin/logout" class="danger">安全登出</a>
      </div>
    </div>

    <div class="admin-grid">

      <div class="card">
        <div class="card-head">已預約時段一覽</div>
        <table class="admin-table">
          <thead>
            <tr>
              <th>星期</th><th>時段</th><th>演出者</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            {admin_rows if admin_rows else "<tr><td colspan='4' class='empty-note'>𝄽 尚無任何預約紀錄</td></tr>"}
          </tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-head">演出者節數統計</div>
        <table class="admin-table">
          <thead>
            <tr><th>姓名</th><th style="text-align:center">已填 / 上限</th></tr>
          </thead>
          <tbody>
            {summary_rows if summary_rows else "<tr><td colspan='2' class='empty-note'>暫無資料</td></tr>"}
          </tbody>
        </table>
      </div>

    </div>
  </div>
</body>
</html>"""

@app.route("/admin/delete", methods=["POST"])
def delete_slot():
    if not session.get("is_admin"):
        return "權限不足！請先登入指揮台。", 403
    day = request.form.get("day")
    slot = request.form.get("slot")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE day = ? AND slot = ?", (day, slot))
        conn.commit()
    return redirect("/admin")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
