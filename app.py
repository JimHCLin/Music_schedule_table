import sqlite3
from datetime import datetime, timezone, timedelta
TZ_TAIPEI = timezone(timedelta(hours=8))
from flask import Flask, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = "x7#m9Z!qP2@sK5wE8$vR"
ADMIN_PASSWORD = "0802"
DB_FILE = "schedule.db"

# ── 設定 ──────────────────────────────────────────────
DAYS  = ["週四", "週五"]
SLOTS = ["第一堂", "第二堂", "第三堂", "第四堂",
         "第五堂", "第六堂", "第七堂", "第八堂"]
MAX_PRIORITY = 3   # 每人最多預約 3 個時段

# ── 資料庫 ────────────────────────────────────────────
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                day          TEXT    NOT NULL,
                slot         TEXT    NOT NULL,
                student_name TEXT    NOT NULL,
                priority     INTEGER NOT NULL,   -- 學生自填 1/2/3
                submitted_at TEXT    NOT NULL,   -- ISO 時間戳
                admin_order  INTEGER             -- 老師手動排序（NULL = 未設定）
            )
        """)
init_db()

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_student_bookings(name):
    """回傳該學生所有預約，依 priority 排序"""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM bookings WHERE student_name=? ORDER BY priority",
            (name,)).fetchall()
    return rows

def get_slot_bookings(day, slot):
    """
    回傳某時段所有預約。
    排序規則：admin_order 優先（NULL 排後），再依 priority，再依 submitted_at
    """
    with db() as conn:
        rows = conn.execute("""
            SELECT * FROM bookings
            WHERE day=? AND slot=?
            ORDER BY
                CASE WHEN admin_order IS NULL THEN 1 ELSE 0 END,
                admin_order,
                priority,
                submitted_at
        """, (day, slot)).fetchall()
    return rows

def get_all_bookings_for_table():
    """
    前台用：每個 (day, slot) 回傳排好的學生列表
    """
    with db() as conn:
        rows = conn.execute("""
            SELECT day, slot, student_name, priority, submitted_at, admin_order
            FROM bookings
            ORDER BY
                day, slot,
                CASE WHEN admin_order IS NULL THEN 1 ELSE 0 END,
                admin_order, priority, submitted_at
        """).fetchall()
    result = {}
    for r in rows:
        key = (r["day"], r["slot"])
        result.setdefault(key, []).append(dict(r))
    return result

# ── CSS / HEAD 共用 ───────────────────────────────────
SHARED_HEAD = """
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Noto+Serif+TC:wght@300;400;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --ink:#07050D;--ink2:#0d0b14;
  --parch:#F5EDD6;--gold:#C9A84C;--gold-dim:#8a6e2f;
  --velvet:#8B1A1A;--mist:#b5a98a;--mist2:#6e6252;
}
body{
  font-family:'Noto Serif TC',serif;
  background:var(--ink);color:var(--parch);
  min-height:100vh;position:relative;overflow-x:hidden;
}
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 60% 40% at 50% 10%,rgba(26,18,40,.9) 0%,transparent 70%),
    radial-gradient(ellipse 80% 60% at 20% 80%,rgba(42,10,10,.4) 0%,transparent 60%),
    radial-gradient(ellipse 80% 60% at 80% 80%,rgba(42,10,10,.4) 0%,transparent 60%);
}
body::after{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:repeating-linear-gradient(
    to bottom,
    transparent 0px,transparent 20px,
    rgba(201,168,76,.055) 20px,rgba(201,168,76,.055) 21px,
    transparent 21px,transparent 24px,
    rgba(201,168,76,.055) 24px,rgba(201,168,76,.055) 25px,
    transparent 25px,transparent 28px,
    rgba(201,168,76,.055) 28px,rgba(201,168,76,.055) 29px,
    transparent 29px,transparent 32px,
    rgba(201,168,76,.055) 32px,rgba(201,168,76,.055) 33px,
    transparent 33px,transparent 36px,
    rgba(201,168,76,.055) 36px,rgba(201,168,76,.055) 37px,
    transparent 37px,transparent 110px
  );
}
.curtain-l,.curtain-r{position:fixed;top:0;bottom:0;width:50px;pointer-events:none;z-index:10}
.curtain-l{left:0;background:linear-gradient(to right,rgba(42,8,8,.55),transparent)}
.curtain-r{right:0;background:linear-gradient(to left,rgba(42,8,8,.55),transparent)}
.arch-deco{
  position:fixed;top:0;left:0;right:0;height:4px;z-index:10;
  background:linear-gradient(to right,transparent 10%,var(--gold-dim) 35%,var(--gold) 50%,var(--gold-dim) 65%,transparent 90%);
  opacity:.55;
}

/* ── 頁面容器 ── */
.page{position:relative;z-index:1;max-width:960px;margin:0 auto;padding:2.5rem 1rem 3rem}

/* ── 標題 ── */
.site-header{text-align:center;margin-bottom:2rem}
.site-title{
  font-family:'Playfair Display',serif;
  font-size:clamp(1.8rem,6vw,3rem);font-weight:700;
  letter-spacing:.1em;color:var(--gold);line-height:1.1;
  text-shadow:0 0 60px rgba(201,168,76,.2),0 2px 4px rgba(0,0,0,.6);
}
.site-title-sub{
  font-family:'Playfair Display',serif;font-style:italic;
  font-size:clamp(.7rem,2.5vw,.9rem);color:var(--parch);opacity:.4;
  letter-spacing:.3em;display:block;margin-top:.4rem;
}
.deco-row{display:flex;align-items:center;justify-content:center;gap:.8rem;margin:.8rem auto;max-width:320px}
.deco-line{flex:1;height:1px;background:linear-gradient(to right,transparent,var(--gold-dim),transparent);opacity:.6}
.deco-clef{font-size:1.2rem;color:var(--gold);opacity:.65}
.site-sub{font-size:.68rem;letter-spacing:.25em;color:var(--mist2);margin-top:.2rem}
.site-sub strong{color:var(--gold)}

/* ── 通知 ── */
.alert{
  border-left:2px solid;padding:.65rem 1rem;margin-bottom:1.4rem;
  font-size:.8rem;border-radius:0 6px 6px 0;
  background:rgba(0,0,0,.3);backdrop-filter:blur(4px);
}
.alert-error{border-color:var(--velvet);color:#f4a0a0}
.alert-success{border-color:#2A3A5E;color:#a0b8f4}

/* ── 前台：預約表單區 ── */
.form-section{
  background:rgba(13,11,20,.92);border:1px solid rgba(201,168,76,.15);
  border-radius:12px;padding:1.5rem;margin-bottom:1.5rem;
  box-shadow:0 0 60px rgba(0,0,0,.6);
  position:relative;z-index:2;
}
.form-section h2{
  font-family:'Playfair Display',serif;font-size:1rem;
  color:var(--gold);letter-spacing:.15em;margin-bottom:1.2rem;
  padding-bottom:.6rem;border-bottom:1px solid rgba(201,168,76,.12);
}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
@media(max-width:500px){.form-grid{grid-template-columns:1fr}}

.form-field label{
  display:block;font-size:.65rem;letter-spacing:.2em;
  color:var(--mist2);text-transform:uppercase;margin-bottom:.35rem;
}
.form-field select,.form-field input[type=text],.form-field input[type=number]{
  width:100%;background:#1a1628;
  border:1px solid rgba(201,168,76,.28);border-radius:6px;
  padding:.65rem .8rem;font-size:1rem;
  font-family:'Noto Serif TC',serif;color:var(--parch);outline:none;
  transition:border-color .2s,box-shadow .2s;
  -webkit-appearance:none;appearance:none;
  position:relative;z-index:1;
  touch-action:manipulation;
  min-height:44px;
}
.form-field select{
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23C9A84C' stroke-width='1.8' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right .8rem center;
  background-color:#1a1628;
  padding-right:2.2rem;
  cursor:pointer;
}
.form-field select option{background:#1a1628;color:var(--parch)}
.form-field select:focus,.form-field input:focus{
  border-color:rgba(201,168,76,.6);box-shadow:0 0 12px rgba(201,168,76,.1);
}

.priority-hint{
  font-size:.68rem;color:var(--mist2);margin-top:.3rem;letter-spacing:.04em;
}

/* ── 按鈕式選單（手機友善） ── */
.btn-group{position:relative;flex:1}
.bg-placeholder{
  width:100%;background:#1a1628;
  border:1px solid rgba(201,168,76,.28);border-radius:6px;
  padding:.65rem .8rem;font-size:.9rem;
  font-family:'Noto Serif TC',serif;color:rgba(181,169,138,.5);
  text-align:left;cursor:pointer;min-height:44px;
  transition:border-color .2s;
}
.bg-placeholder.selected{color:var(--parch);border-color:rgba(201,168,76,.5)}
.bg-options{
  position:absolute;top:calc(100% + 4px);left:0;right:0;
  background:#1a1628;border:1px solid rgba(201,168,76,.3);
  border-radius:8px;z-index:100;
  box-shadow:0 8px 30px rgba(0,0,0,.7);
  overflow:hidden;
}
.bg-opt{
  display:block;width:100%;background:none;border:none;border-bottom:1px solid rgba(201,168,76,.08);
  padding:.75rem 1rem;font-size:.9rem;
  font-family:'Noto Serif TC',serif;color:var(--parch);
  text-align:left;cursor:pointer;min-height:44px;
  transition:background .15s;
}
.bg-opt:last-child{border-bottom:none}
.bg-opt:hover,.bg-opt:active{background:rgba(201,168,76,.12);color:var(--gold)}

/* 優先序標籤 */
.priority-slots{display:flex;flex-direction:column;gap:.5rem;margin-top:.8rem}
.priority-row{
  display:grid;grid-template-columns:24px 1fr 1fr;
  gap:.5rem;align-items:center;
}
.priority-num{
  width:22px;height:22px;border-radius:50%;
  border:1px solid rgba(201,168,76,.4);
  color:var(--gold);font-size:.7rem;font-weight:600;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;
}

.submit-btn{
  margin-top:1.2rem;width:100%;
  background:linear-gradient(135deg,#9a7628 0%,#c9a84c 40%,#d4b55a 55%,#b8922a 100%);
  color:#1a1000;font-family:'Playfair Display',serif;
  font-size:.88rem;font-weight:700;letter-spacing:.18em;
  padding:.8rem;border:none;border-radius:7px;cursor:pointer;
  box-shadow:0 4px 20px rgba(201,168,76,.2);
  transition:opacity .2s,transform .12s;
}
.submit-btn:hover{opacity:.88}
.submit-btn:active{transform:scale(.97)}

/* ── 前台：課表展示 ── */
.schedule-section{margin-top:1.8rem}
.schedule-section h2{
  font-family:'Playfair Display',serif;font-size:1rem;
  color:var(--gold);letter-spacing:.15em;margin-bottom:1rem;
  padding-bottom:.6rem;border-bottom:1px solid rgba(201,168,76,.12);
}

/* 手機友善：改用卡片式 */
.day-block{margin-bottom:1.4rem}
.day-title{
  font-family:'Playfair Display',serif;font-size:.85rem;
  letter-spacing:.2em;color:var(--gold);
  background:rgba(7,5,13,.8);border:1px solid rgba(201,168,76,.18);
  border-radius:8px 8px 0 0;padding:.6rem 1rem;
}
.slot-row{
  background:rgba(13,11,20,.6);
  border:1px solid rgba(201,168,76,.07);border-top:none;
  padding:.7rem 1rem;
  display:flex;align-items:flex-start;gap:.8rem;
}
.slot-row:last-child{border-radius:0 0 8px 8px}
.slot-name{
  font-family:'Playfair Display',serif;font-style:italic;
  color:var(--gold-dim);font-size:.78rem;min-width:56px;
  padding-top:.05rem;
}
.slot-students{flex:1;display:flex;flex-wrap:wrap;gap:.4rem}
.student-chip{
  display:inline-flex;align-items:center;gap:.3rem;
  background:rgba(80,10,10,.18);border:1px solid rgba(139,26,26,.3);
  border-radius:20px;padding:.2rem .65rem;
  font-size:.72rem;color:#d89090;letter-spacing:.03em;
}
.student-chip .rank{
  width:16px;height:16px;border-radius:50%;
  background:rgba(80,80,80,.15);border:1px solid rgba(180,169,138,.2);
  color:var(--mist2);font-size:.6rem;font-weight:700;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;
}
.student-chip .rank.p1{background:rgba(201,168,76,.2);border-color:rgba(201,168,76,.5);color:var(--gold)}
.student-chip .rank.p2{background:rgba(42,58,94,.25);border-color:rgba(80,110,180,.35);color:#8aaae8}
.student-chip .rank.p3{background:rgba(40,80,40,.2);border-color:rgba(80,160,80,.3);color:#88c888}
.slot-empty{font-size:.72rem;color:var(--mist2);font-style:italic;opacity:.6}

/* ── 頁尾 ── */
.page-footer{
  display:flex;justify-content:space-between;align-items:center;
  margin-top:2rem;padding-top:1rem;
  border-top:1px solid rgba(201,168,76,.08);
  font-size:.7rem;color:var(--mist2);letter-spacing:.1em;
  flex-wrap:wrap;gap:.5rem;
}
.page-footer a{color:var(--gold-dim);text-decoration:none;transition:color .2s}
.page-footer a:hover{color:var(--gold)}

/* ── 登入頁 ── */
.login-stage{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}
.login-card{
  background:rgba(13,11,20,.88);border:1px solid rgba(201,168,76,.18);
  border-radius:16px;padding:2.5rem 2rem;width:100%;max-width:340px;
  text-align:center;backdrop-filter:blur(12px);
  box-shadow:0 0 100px rgba(0,0,0,.8);position:relative;
}
.login-card::before{
  content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);
  width:180px;height:2px;
  background:linear-gradient(to right,transparent,var(--gold-dim),transparent);
  opacity:.5;border-radius:1px;
}
.login-clef{font-size:2.4rem;color:var(--gold);opacity:.5;display:block;margin-bottom:.9rem;line-height:1;text-shadow:0 0 30px rgba(201,168,76,.3)}
.login-title{font-family:'Playfair Display',serif;font-size:1.4rem;color:var(--gold);letter-spacing:.18em;margin-bottom:.2rem}
.login-sub{font-size:.6rem;letter-spacing:.32em;color:var(--mist2);text-transform:uppercase;margin-bottom:1.8rem}
.login-label{display:block;text-align:left;font-size:.63rem;letter-spacing:.2em;color:var(--mist2);margin-bottom:.5rem;text-transform:uppercase}
.login-input{
  width:100%;background:rgba(245,237,214,.04);
  border:1px solid rgba(201,168,76,.2);border-radius:7px;
  padding:.7rem 1rem;font-size:.9rem;font-family:'Noto Serif TC',serif;
  color:var(--parch);text-align:center;letter-spacing:.3em;
  outline:none;transition:border-color .2s,box-shadow .2s;margin-bottom:1.2rem;
}
.login-input:focus{border-color:rgba(201,168,76,.45);box-shadow:0 0 20px rgba(201,168,76,.08)}
.login-btn{
  width:100%;
  background:linear-gradient(135deg,#9a7628 0%,#c9a84c 40%,#d4b55a 55%,#b8922a 100%);
  color:#1a1000;font-family:'Playfair Display',serif;font-size:.85rem;
  font-weight:700;letter-spacing:.22em;padding:.78rem;
  border:none;border-radius:7px;cursor:pointer;
  box-shadow:0 4px 20px rgba(201,168,76,.2);transition:opacity .2s,transform .12s;
}
.login-btn:hover{opacity:.88}
.login-btn:active{transform:scale(.97)}
.login-back{display:block;margin-top:1.4rem;font-size:.67rem;color:var(--mist2);text-decoration:none;letter-spacing:.15em;transition:color .2s}
.login-back:hover{color:var(--gold)}

/* ── 後台 ── */
.admin-wrap{position:relative;z-index:1;max-width:1000px;margin:0 auto;padding:1.5rem 1rem 3rem}
.admin-header{
  display:flex;justify-content:space-between;align-items:flex-end;
  margin-bottom:1.5rem;padding-bottom:.8rem;
  border-bottom:1px solid rgba(201,168,76,.12);flex-wrap:wrap;gap:.6rem;
}
.admin-title{font-family:'Playfair Display',serif;font-size:1.25rem;color:var(--gold);letter-spacing:.1em}
.admin-sub{font-size:.63rem;color:var(--mist2);margin-top:.2rem;letter-spacing:.15em}
.admin-links{display:flex;gap:1.2rem;font-size:.7rem}
.admin-links a{color:var(--mist2);text-decoration:none;letter-spacing:.1em;transition:color .2s}
.admin-links a:hover{color:var(--gold)}
.admin-links a.danger:hover{color:#f4a0a0}

/* 後台：每個時段 block */
.admin-day-section{margin-bottom:1.8rem}
.admin-day-title{
  font-family:'Playfair Display',serif;font-size:.9rem;
  letter-spacing:.2em;color:var(--gold);
  padding:.5rem .9rem;background:rgba(7,5,13,.8);
  border:1px solid rgba(201,168,76,.18);border-radius:8px;
  margin-bottom:.6rem;display:inline-block;
}
.admin-slot-card{
  background:rgba(13,11,20,.75);border:1px solid rgba(201,168,76,.1);
  border-radius:8px;margin-bottom:.6rem;overflow:hidden;
}
.admin-slot-head{
  background:rgba(7,5,13,.7);padding:.5rem .9rem;
  border-bottom:1px solid rgba(201,168,76,.08);
  font-family:'Playfair Display',serif;font-style:italic;
  font-size:.8rem;color:var(--gold-dim);letter-spacing:.05em;
}
.admin-booking-row{
  display:flex;flex-direction:column;gap:.6rem;
  padding:.9rem;
  border-bottom:1px solid rgba(201,168,76,.07);
}
.admin-booking-row:last-child{border-bottom:none}

.admin-row-top{display:flex;align-items:center;gap:.7rem}
.admin-row-actions{display:flex;flex-wrap:wrap;gap:.5rem;padding-left:32px}

.rank-badge{
  width:28px;height:28px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:.75rem;font-weight:700;flex-shrink:0;
}
.rank-1{background:rgba(201,168,76,.2);border:1px solid rgba(201,168,76,.5);color:var(--gold)}
.rank-other{background:rgba(80,80,80,.15);border:1px solid rgba(180,169,138,.15);color:var(--mist2)}

.booking-info{min-width:0;flex:1}
.booking-name{font-size:.9rem;color:var(--parch);font-weight:600}
.booking-meta{font-size:.68rem;color:var(--mist2);margin-top:.15rem}
.student-priority{
  display:inline-block;font-size:.62rem;
  background:rgba(201,168,76,.1);border:1px solid rgba(201,168,76,.25);
  border-radius:10px;padding:.05rem .4rem;color:var(--gold-dim);
}

/* 操作群組標籤 */
.action-group{display:flex;align-items:center;gap:.35rem}
.action-label{font-size:.6rem;color:var(--mist2);letter-spacing:.08em;white-space:nowrap}

.order-form{display:flex;align-items:center;gap:.35rem}
.order-btn{
  background:rgba(20,18,28,.8);
  border:1px solid rgba(201,168,76,.3);
  color:var(--gold-dim);
  font-size:.82rem;
  min-width:44px;min-height:44px;
  padding:.3rem .6rem;
  border-radius:6px;cursor:pointer;
  font-family:'Noto Serif TC',serif;
  display:flex;align-items:center;justify-content:center;
  transition:background .18s,color .18s,border-color .18s;
}
.order-btn:hover{background:rgba(201,168,76,.12);color:var(--gold);border-color:rgba(201,168,76,.5)}
.order-btn:active{transform:scale(.95)}

.del-btn{
  background:rgba(20,18,28,.8);
  border:1px solid rgba(139,26,26,.45);
  color:#b07070;
  font-size:.82rem;
  min-width:44px;min-height:44px;
  padding:.3rem .8rem;
  border-radius:6px;cursor:pointer;
  font-family:'Noto Serif TC',serif;
  display:flex;align-items:center;justify-content:center;
  transition:background .18s,color .18s;
}
.del-btn:hover{background:rgba(139,26,26,.2);color:#f4a0a0}
.del-btn:active{transform:scale(.95)}
.order-btn.pri-active{background:rgba(201,168,76,.18);border-color:rgba(201,168,76,.65);color:var(--gold)}

.empty-note{text-align:center;padding:2rem;color:var(--mist2);font-size:.75rem;font-style:italic;opacity:.7}

/* 後台統計 */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:.7rem;margin-bottom:1.5rem}
.stat-card{
  background:rgba(13,11,20,.75);border:1px solid rgba(201,168,76,.1);
  border-radius:8px;padding:.8rem;text-align:center;
}
.stat-name{font-size:.72rem;color:var(--mist2);margin-bottom:.3rem;letter-spacing:.05em}
.stat-count{font-size:1.3rem;font-weight:700;color:var(--gold)}
.stat-limit{font-size:.65rem;color:var(--mist2)}

/* 手機 */
@media(max-width:480px){
  .admin-wrap{padding:1rem .7rem 3rem}
  .page{padding:2rem .8rem 3rem}
  .admin-row-actions{padding-left:0}
}
</style>
"""

BTN_JS = """<script>
function toggleGroup(btn){
  var opts=btn.nextElementSibling;
  document.querySelectorAll(".bg-options").forEach(function(el){if(el!==opts)el.style.display="none";});
  opts.style.display=opts.style.display==="none"?"block":"none";
}
function selectOpt(btn){
  var g=btn.closest(".btn-group");
  g.querySelector("input[type=hidden]").value=btn.dataset.val;
  var ph=g.querySelector(".bg-placeholder");
  ph.textContent=btn.dataset.val+" \u2713";
  ph.classList.add("selected");
  btn.closest(".bg-options").style.display="none";
}
document.addEventListener("click",function(e){
  if(!e.target.closest(".btn-group"))
    document.querySelectorAll(".bg-options").forEach(function(el){el.style.display="none";});
});
</script>"""



# ── 前台主頁 ──────────────────────────────────────────
@app.route("/")
def index_page():
    error   = request.args.get("error", "")
    success = request.args.get("success", "")
    all_bookings = get_all_bookings_for_table()

    # ── 課表展示 ──
    schedule_html = ""
    for day in DAYS:
        schedule_html += f"<div class='day-block'><div class='day-title'>{day}</div>"
        for slot in SLOTS:
            students = all_bookings.get((day, slot), [])
            schedule_html += "<div class='slot-row'>"
            schedule_html += f"<span class='slot-name'>{slot}</span>"
            schedule_html += "<div class='slot-students'>"
            if students:
                for s in students:
                    p = s['priority']
                    schedule_html += (
                        f"<span class='student-chip'>"
                        f"<span class='rank p{p}'>{p}</span>"
                        f"♩ {s['student_name']}"
                        f"</span>"
                    )
            else:
                schedule_html += "<span class='slot-empty'>尚無預約</span>"
            schedule_html += "</div></div>"
        schedule_html += "</div>"

    alert_html = ""
    if error:
        alert_html = f"<div class='alert alert-error'>⚠ {error}</div>"
    elif success:
        alert_html = f"<div class='alert alert-success'>✦ {success}</div>"

    # ── 優先序選擇欄（按鈕式，手機友善）──
    def btn_group(name, options, placeholder):
        btns = f"<div class='btn-group' data-name='{name}'>"
        btns += f"<input type='hidden' name='{name}' value='' required>"
        btns += f"<button type='button' class='bg-placeholder' onclick='toggleGroup(this)'>{placeholder} ▾</button>"
        btns += f"<div class='bg-options' style='display:none'>"
        for val in options:
            btns += f"<button type='button' class='bg-opt' onclick='selectOpt(this)' data-val='{val}'>{val}</button>"
        btns += "</div></div>"
        return btns

    priority_rows = ""
    for p in range(1, MAX_PRIORITY + 1):
        priority_rows += f"""
        <div class='priority-row'>
          <span class='priority-num'>{p}</span>
          {btn_group(f'day_{p}', DAYS, '選擇星期')}
          {btn_group(f'slot_{p}', SLOTS, '選擇堂數')}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><title>樂章共鳴 · 時段預約</title>{SHARED_HEAD}</head>
<body>
<div class="arch-deco"></div>
<div class="curtain-l"></div>
<div class="curtain-r"></div>
<div class="page">

  <header class="site-header">
    <h1 class="site-title">樂章共鳴
      <span class="site-title-sub">H a r m o n i a &nbsp;·&nbsp; 時 段 預 約</span>
    </h1>
    <div class="deco-row">
      <div class="deco-line"></div>
      <span class="deco-clef">𝄞</span>
      <div class="deco-line"></div>
    </div>
    <p class="site-sub">每人可選 <strong>{MAX_PRIORITY}</strong> 個時段，依優先順序 1 → 2 → 3 填入</p>
  </header>

  {alert_html}

  <div class="form-section">
    <h2>♩ 填寫預約志願</h2>
    <form action="/book" method="post">
      <div class="form-field" style="margin-bottom:.9rem">
        <label>你的姓名</label>
        <input type="text" name="name" placeholder="請輸入姓名" required>
      </div>
      <div class="priority-hint" style="margin-bottom:.6rem">
        請依照你的希望順序，選擇最多 {MAX_PRIORITY} 個時段（第 1 志願最優先）
      </div>
      <div class="priority-slots">
        {priority_rows}
      </div>
      <button type="submit" class="submit-btn">送出預約志願</button>
    </form>
  </div>

  <div class="schedule-section">
    <h2>♬ 目前預約狀況</h2>
    {schedule_html}
  </div>

  <footer class="page-footer">
    <span>🎻 週四・週五 · 各 8 堂</span>
    <span style="color:var(--mist2);font-size:.62rem;letter-spacing:.1em">v1.5</span>
    <a href="/admin">指揮台後台 →</a>
  </footer>
</div>
{BTN_JS}
</body>
</html>"""

# ── 送出預約 ──────────────────────────────────────────
@app.route("/book", methods=["POST"])
def book_slot():
    name = request.form.get("name", "").strip()
    if not name:
        return redirect("/?error=姓名不能為空")

    # 收集三個志願
    entries = []
    for p in range(1, MAX_PRIORITY + 1):
        day  = request.form.get(f"day_{p}", "").strip()
        slot = request.form.get(f"slot_{p}", "").strip()
        if day and slot and day in DAYS and slot in SLOTS:
            entries.append((day, slot, p))

    if not entries:
        return redirect("/?error=請至少選擇一個時段")

    # 去重（同一志願不能選同樣時段兩次）
    seen = set()
    unique_entries = []
    for day, slot, p in entries:
        if (day, slot) not in seen:
            seen.add((day, slot))
            unique_entries.append((day, slot, p))

    now_str = datetime.now(TZ_TAIPEI).strftime("%Y-%m-%dT%H:%M:%S")
    with db() as conn:
        # 確認此學生尚未預約（同一人不重複送出）
        existing = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE student_name=?", (name,)
        ).fetchone()[0]
        if existing > 0:
            return redirect(f"/?error=【{name}】已送出過預約，若需修改請聯繫老師")

        for day, slot, priority in unique_entries:
            conn.execute("""
                INSERT INTO bookings (day, slot, student_name, priority, submitted_at)
                VALUES (?, ?, ?, ?, ?)
            """, (day, slot, name, priority, now_str))
        conn.commit()

    slots_desc = "、".join(f"{d}{s}（第{p}志願）" for d, s, p in unique_entries)
    return redirect(f"/?success=【{name}】已完成預約：{slots_desc}")

# ── 後台登入 ──────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error_msg = ""
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect("/admin")
        error_msg = "<div class='alert alert-error' style='margin-bottom:1.2rem;text-align:left'>✕ 密鑰不符</div>"
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><title>指揮台 · 登入</title>{SHARED_HEAD}</head>
<body>
<div class="arch-deco"></div>
<div class="curtain-l"></div>
<div class="curtain-r"></div>
<div class="login-stage">
  <div class="login-card">
    <span class="login-clef">𝄢</span>
    <h2 class="login-title">後台指揮室</h2>
    <p class="login-sub">Conductor Control Room</p>
    {error_msg}
    <form method="post">
      <label class="login-label">輸入指揮密鑰</label>
      <input type="password" name="password" required class="login-input" placeholder="· · · ·">
      <button type="submit" class="login-btn">解 鎖 控 制 台</button>
    </form>
    <a href="/" class="login-back">← 返回前台</a>
  </div>
</div>
</body>
</html>"""

# ── 後台主頁 ──────────────────────────────────────────
@app.route("/admin")
def admin_page():
    if not session.get("is_admin"):
        return redirect("/admin/login")

    # 每個時段排序後的預約
    slot_sections = ""
    for day in DAYS:
        slot_sections += f"<div class='admin-day-section'><div class='admin-day-title'>{day}</div>"
        for slot in SLOTS:
            rows = get_slot_bookings(day, slot)
            slot_sections += f"<div class='admin-slot-card'><div class='admin-slot-head'>{slot}</div>"
            if not rows:
                slot_sections += "<div class='empty-note'>尚無預約</div>"
            else:
                for rank, r in enumerate(rows, 1):
                    badge_cls = "rank-1" if rank == 1 else "rank-other"
                    dt = r["submitted_at"][:16].replace("T", " ") if r["submitted_at"] else ""
                    cur_order = r["admin_order"] if r["admin_order"] is not None else ""
                    slot_sections += f"""
                    <div class='admin-booking-row'>
                      <div class='admin-row-top'>
                        <span class='rank-badge {badge_cls}'>{rank}</span>
                        <div class='booking-info'>
                          <div class='booking-name'>{r['student_name']}</div>
                          <div class='booking-meta'>填表時間：{dt}</div>
                        </div>
                      </div>
                      <div class='admin-row-actions'>
                        <div class='action-group'>
                          <span class='action-label'>志願序</span>
                          <form action='/admin/set_priority' method='post' style='display:inline'>
                            <input type='hidden' name='booking_id' value='{r["id"]}'>
                            <input type='hidden' name='priority_val' value='1'>
                            <button type='submit' class='order-btn {"pri-active" if r["priority"]==1 else ""}'>①</button>
                          </form>
                          <form action='/admin/set_priority' method='post' style='display:inline'>
                            <input type='hidden' name='booking_id' value='{r["id"]}'>
                            <input type='hidden' name='priority_val' value='2'>
                            <button type='submit' class='order-btn {"pri-active" if r["priority"]==2 else ""}'>②</button>
                          </form>
                          <form action='/admin/set_priority' method='post' style='display:inline'>
                            <input type='hidden' name='booking_id' value='{r["id"]}'>
                            <input type='hidden' name='priority_val' value='3'>
                            <button type='submit' class='order-btn {"pri-active" if r["priority"]==3 else ""}'>③</button>
                          </form>
                        </div>
                        <div class='action-group'>
                          <span class='action-label'>排名</span>
                          <form action='/admin/reorder' method='post' style='display:inline'>
                            <input type='hidden' name='booking_id' value='{r["id"]}'>
                            <input type='hidden' name='day' value='{day}'>
                            <input type='hidden' name='slot' value='{slot}'>
                            <input type='hidden' name='direction' value='up'>
                            <button type='submit' class='order-btn'>↑</button>
                          </form>
                          <form action='/admin/reorder' method='post' style='display:inline'>
                            <input type='hidden' name='booking_id' value='{r["id"]}'>
                            <input type='hidden' name='day' value='{day}'>
                            <input type='hidden' name='slot' value='{slot}'>
                            <input type='hidden' name='direction' value='down'>
                            <button type='submit' class='order-btn'>↓</button>
                          </form>
                        </div>
                        <form action='/admin/delete' method='post' style='display:inline'>
                          <input type='hidden' name='booking_id' value='{r["id"]}'>
                          <button type='submit' class='del-btn'
                            onclick="return confirm('確定刪除？')">刪除</button>
                        </form>
                      </div>
                    </div>"""
            slot_sections += "</div>"
        slot_sections += "</div>"

    # 學生統計
    with db() as conn:
        students = conn.execute("""
            SELECT student_name, COUNT(*) as cnt
            FROM bookings GROUP BY student_name ORDER BY student_name
        """).fetchall()

    stats_html = ""
    for s in students:
        stats_html += f"""
        <div class='stat-card'>
          <div class='stat-name'>{s['student_name']}</div>
          <div class='stat-count'>{s['cnt']}</div>
          <div class='stat-limit'>/ {MAX_PRIORITY} 志願</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><title>指揮台管理中心</title>{SHARED_HEAD}</head>
<body>
<div class="arch-deco"></div>
<div class="curtain-l"></div>
<div class="curtain-r"></div>
<div class="admin-wrap">
  <div class="admin-header">
    <div>
      <div class="admin-title">🎻 指揮台管理中心</div>
      <div class="admin-sub">依時段查看所有預約 · 可手動調整優先順序</div>
    </div>
    <div class="admin-links">
      <a href="/">← 前台</a>
      <a href="/admin/logout" class="danger">登出</a>
    </div>
  </div>

  <div style="margin-bottom:1.2rem">
    <div style="font-size:.63rem;letter-spacing:.2em;color:var(--mist2);text-transform:uppercase;margin-bottom:.6rem">學生預約總覽</div>
    <div class="stats-grid">{stats_html if stats_html else "<span style='color:var(--mist2);font-size:.78rem;font-style:italic'>尚無資料</span>"}</div>
  </div>

  <!-- 操作說明 -->
  <div style="background:rgba(13,11,20,.75);border:1px solid rgba(201,168,76,.12);border-radius:10px;padding:1rem 1.2rem;margin-bottom:1.2rem">
    <div style="font-size:.65rem;letter-spacing:.2em;color:var(--gold-dim);text-transform:uppercase;margin-bottom:.7rem">操作說明</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.8rem">
      <div style="background:rgba(7,5,13,.5);border-radius:7px;padding:.7rem .9rem;border-left:2px solid rgba(201,168,76,.3)">
        <div style="font-size:.75rem;color:var(--gold);font-weight:600;margin-bottom:.35rem">左側數字圓圈</div>
        <div style="font-size:.7rem;color:var(--mist2);line-height:1.6">
          系統自動排名，金色①＝當前第1順位。<br>依<b style="color:var(--mist)">填表時間早晚</b>自動決定，最早填的排第1。
        </div>
      </div>
      <div style="background:rgba(7,5,13,.5);border-radius:7px;padding:.7rem .9rem;border-left:2px solid rgba(42,90,160,.4)">
        <div style="font-size:.75rem;color:#8aaae8;font-weight:600;margin-bottom:.35rem">志願序 ① ② ③</div>
        <div style="font-size:.7rem;color:var(--mist2);line-height:1.6">
          修改<b style="color:var(--mist)">前台圓圈數字</b>。<br>金色高亮＝目前志願序。點任一個按鈕即可直接更改，前台立即更新。
        </div>
      </div>
      <div style="background:rgba(7,5,13,.5);border-radius:7px;padding:.7rem .9rem;border-left:2px solid rgba(80,160,80,.3)">
        <div style="font-size:.75rem;color:#88c888;font-weight:600;margin-bottom:.35rem">排名 ↑ ↓</div>
        <div style="font-size:.7rem;color:var(--mist2);line-height:1.6">
          手動調整<b style="color:var(--mist)">後台排名順序</b>。<br>↑ 讓此人往前一位，↓ 往後一位。多人預約同一時段時使用。
        </div>
      </div>
      <div style="background:rgba(7,5,13,.5);border-radius:7px;padding:.7rem .9rem;border-left:2px solid rgba(139,26,26,.4)">
        <div style="font-size:.75rem;color:#d89090;font-weight:600;margin-bottom:.35rem">刪除</div>
        <div style="font-size:.7rem;color:var(--mist2);line-height:1.6">
          移除這筆預約，學生可重新至前台填表。<br>點後會跳出確認視窗。
        </div>
      </div>
    </div>
  </div>

  <div style="font-size:.63rem;letter-spacing:.2em;color:var(--mist2);text-transform:uppercase;margin-bottom:.8rem">
    各時段預約排序
    <span style="font-size:.6rem;opacity:.6;margin-left:.5rem">（左側圓圈＝系統排名 · 金色①＝第1順位 · 志願數字＝學生自填）</span>
  </div>
  {slot_sections}
</div>
</body>
</html>"""

# ── 後台：手動設定排序 ──────────────────────────────────
@app.route("/admin/set_priority", methods=["POST"])
def admin_set_priority():
    if not session.get("is_admin"):
        return "權限不足", 403
    booking_id   = request.form.get("booking_id")
    priority_val = request.form.get("priority_val", "1").strip()
    try:
        p = int(priority_val)
        if p not in (1, 2, 3):
            p = 1
    except ValueError:
        p = 1
    with db() as conn:
        conn.execute("UPDATE bookings SET priority=? WHERE id=?", (p, booking_id))
        conn.commit()
    return redirect("/admin")

@app.route("/admin/reorder", methods=["POST"])
def admin_reorder():
    if not session.get("is_admin"):
        return "権限不足", 403
    booking_id = int(request.form.get("booking_id", 0))
    direction  = request.form.get("direction", "")
    day        = request.form.get("day")
    slot       = request.form.get("slot")

    with db() as conn:
        rows = conn.execute("""
            SELECT id FROM bookings WHERE day=? AND slot=?
            ORDER BY
                CASE WHEN admin_order IS NULL THEN 1 ELSE 0 END,
                admin_order, priority, submitted_at
        """, (day, slot)).fetchall()
        ids = [r["id"] for r in rows]

        if booking_id in ids:
            idx = ids.index(booking_id)
            if direction == "up" and idx > 0:
                ids[idx], ids[idx-1] = ids[idx-1], ids[idx]
            elif direction == "down" and idx < len(ids)-1:
                ids[idx], ids[idx+1] = ids[idx+1], ids[idx]
            for new_order, bid in enumerate(ids, 1):
                conn.execute("UPDATE bookings SET admin_order=? WHERE id=?", (new_order, bid))
            conn.commit()
    return redirect("/admin")

# ── 後台：刪除單筆預約 ────────────────────────────────
@app.route("/admin/delete", methods=["POST"])
def delete_booking():
    if not session.get("is_admin"):
        return "權限不足", 403
    booking_id = request.form.get("booking_id")
    with db() as conn:
        conn.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
        conn.commit()
    return redirect("/admin")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
