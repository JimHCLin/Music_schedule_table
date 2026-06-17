import sqlite3
from flask import Flask, request, redirect, session

app = Flask(__name__)

# --- 🔒 安全設定 ---
app.secret_key = "x7#m9Z!qP2@sK5wE8$vR"  # 已幫你換成安全的防偽亂碼鋼印
ADMIN_PASSWORD = "0802"                  # 你的專屬後台登入密碼

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

# --- 🎼 前端：藝術風課表主頁 ---
@app.route("/")
def index_page():
    error = request.args.get("error", "")
    success = request.args.get("success", "")
    bookings = get_all_bookings()
    
    table_rows = ""
    for slot in SLOTS:
        table_rows += f"<tr class='border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors'>"
        table_rows += f"<td class='p-4 bg-slate-900/80 font-medium text-amber-400/90 text-center border-r border-slate-800'>{slot}</td>"
        for day in DAYS:
            name = bookings.get((day, slot), "")
            if name:
                # 已被登記：優雅的絲絨紅與樂章保留感
                table_rows += f"<td class='p-4 bg-rose-950/20 text-rose-300 font-medium text-center border-r border-slate-800/40 shadow-inner'>🎵 {name} 的專屬樂章</td>"
            else:
                # 尚可登記：像鋼琴琴鍵般的極簡輸入框
                table_rows += f"""
                <td class='p-3 text-center border-r border-slate-800/40'>
                    <form action='/book' method='post' class='flex gap-2 justify-center items-center'>
                        <input type='hidden' name='day' value='{day}'>
                        <input type='hidden' name='slot' value='{slot}'>
                        <input type='text' name='name' placeholder='吟唱者姓名' required 
                               class='bg-slate-900/60 border border-slate-700/50 rounded-md px-2 py-1 text-xs text-slate-200 w-24 text-center placeholder-slate-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all'>
                        <button type='submit' class='bg-gradient-to-b from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 text-xs font-bold px-2.5 py-1 rounded shadow-md active:scale-95 transition-all cursor-pointer'>預約</button>
                    </form>
                </td>
                """
        table_rows += "</tr>"

    alert_html = ""
    if error:
        alert_html = f"<div class='bg-rose-950/40 border border-rose-800/60 text-rose-300 px-4 py-3 rounded-lg mb-6 text-center text-sm backdrop-blur-sm'>⚠️ {error}</div>"
    elif success:
        alert_html = f"<div class='bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 px-4 py-3 rounded-lg mb-6 text-center text-sm backdrop-blur-sm'>✨ {success}</div>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>樂章共鳴：時段預約表</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <style>
            body {{ background-image: radial-gradient(circle at top, #1e1b4b 0%, #020617 100%); }}
        </style>
    </head>
    <body class="text-slate-200 min-h-screen p-4 md:p-8 flex items-center justify-center">
        <div class="w-full max-w-6xl bg-slate-900/40 backdrop-blur-md p-6 md:p-10 rounded-2xl shadow-2xl border border-slate-800/80">
            
            <div class="text-center mb-8">
                <h1 class="text-4xl font-extrabold tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-amber-400 to-amber-200 mb-3 drop-shadow-sm">
                    🎼 樂章共鳴：線上時段預約表
                </h1>
                <p class="text-slate-400 text-xs tracking-widest uppercase">
                    尋找你的專屬節奏 ‧ 每人上限演繹 <span class="text-amber-400 font-bold">5</span> 個時段
                </p>
            </div>

            {alert_html}

            <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/20 shadow-xl">
                <table class="w-full border-collapse text-sm">
                    <thead>
                        <tr class="bg-slate-900/90 text-slate-400 border-b border-slate-800">
                            <th class="p-4 w-32 font-medium tracking-wider text-amber-400/80 text-center">時段 \ 星期</th>
                            {"".join(f"<th class='p-4 font-semibold tracking-widest text-center border-r border-slate-800/40'>{day}</th>" for day in DAYS)}
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>

            <div class="mt-8 flex justify-between items-center text-xs text-slate-500 px-2">
                <div>🎻 琴房容納上限：10 人</div>
                <a href="/admin" class="hover:text-amber-400 transition-colors underline underline-offset-4 tracking-wider">🎹 進入後台指揮台</a>
            </div>
        </div>
    </body>
    </html>
    """

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
            return redirect(f"/?error=已達 5 個時段演繹上限。")
        
        try:
            cursor.execute("INSERT INTO bookings (day, slot, student_name) VALUES (?, ?, ?)", (day, slot, name))
            conn.commit()
        except sqlite3.IntegrityError:
            return redirect("/?error=此時段已被其他演出者捷足先登。")
            
    return redirect(f"/?success=【{name}】已成功預約 {day} {slot}。")

# --- 🔐 後台：後台控制室登入 ---
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error_msg = ""
    if request.method == "POST":
        input_password = request.form.get("password")
        if input_password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect("/admin")
        else:
            error_msg = "<p class='text-rose-400 text-xs mb-3 text-center tracking-wide'>❌ 密鑰不符，無法開啟指揮門</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>後台控制室</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <style>
            body {{ background-image: radial-gradient(circle at center, #1e1b4b 0%, #020617 100%); }}
        </style>
    </head>
    <body class="text-slate-200 flex items-center justify-center h-screen p-4">
        <div class="bg-slate-900/60 backdrop-blur-md p-8 rounded-2xl shadow-2xl w-full max-w-sm border border-slate-800 text-center">
            <div class="text-3xl mb-3">🎹</div>
            <h2 class="text-xl font-bold mb-1 tracking-widest text-amber-400">後台指揮室</h2>
            <p class="text-slate-500 text-xs mb-6 tracking-wider uppercase">Conductor Control Room</p>
            {error_msg}
            <form method="post" class="text-left">
                <div class="mb-5">
                    <label class="block text-slate-400 text-xs font-medium mb-2 tracking-wider">輸入指揮密鑰 (Password)</label>
                    <input type="password" name="password" required 
                           class="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all text-center tracking-widest">
                </div>
                <button type="submit" class="w-full bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold py-2.5 rounded-lg shadow-lg active:scale-[0.98] transition-all cursor-pointer tracking-widest text-sm">解鎖控制台</button>
            </form>
            <div class="mt-6">
                <a href="/" class="text-xs text-slate-500 hover:text-slate-300 transition-colors underline underline-offset-4">⬅️ 返回前台樂章</a>
            </div>
        </div>
    </body>
    </html>
    """

# --- 🎻 後台：指揮台管理中心 ---
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
                <tr class='border-b border-slate-800 hover:bg-slate-800/30 transition-colors text-sm'>
                    <td class='px-6 py-3.5 font-medium text-slate-300'>{day}</td>
                    <td class='px-6 py-3.5 text-amber-400/80'>{slot}</td>
                    <td class='px-6 py-3.5 font-semibold text-rose-300'>✨ {name}</td>
                    <td class='px-6 py-3.5 text-center'>
                        <form action='/admin/delete' method='post'>
                            <input type='hidden' name='day' value='{day}'>
                            <input type='hidden' name='slot' value='{slot}'>
                            <button type='submit' class='bg-rose-950/60 hover:bg-rose-900 border border-rose-800/50 text-rose-300 text-xs px-3 py-1 rounded-md transition-all cursor-pointer active:scale-95'>變更/取消</button>
                        </form>
                    </td>
                </tr>
                """
                
    student_summary_rows = "".join(
        f"<tr class='border-b border-slate-800 hover:bg-slate-800/20'><td class='px-4 py-3 text-slate-300'>{s}</td><td class='px-4 py-3 text-center font-bold text-amber-400'>{c} / 5 節</td></tr>"
        for s, c in student_counts.items()
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>指揮台管理中心</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <style>
            body {{ background-image: radial-gradient(circle at top, #0f172a 0%, #020617 100%); }}
        </style>
    </head>
    <body class="text-slate-200 min-h-screen p-4 md:p-8">
        <div class="max-w-6xl mx-auto flex flex-col lg:flex-row gap-6">
            
            <div class="flex-1 bg-slate-900/50 backdrop-blur-md p-6 rounded-2xl shadow-xl border border-slate-800">
                <div class="flex justify-between items-center mb-6 pb-4 border-b border-slate-800">
                    <div>
                        <h2 class="text-xl font-bold text-amber-400 tracking-wider">🎻 指揮台：預約節目清單</h2>
                        <p class="text-slate-500 text-xs mt-1">目前所有已被演繹的時間點</p>
                    </div>
                    <div class="flex gap-4 text-xs">
                        <a href="/" class="text-amber-400/80 hover:text-amber-300 transition-colors underline underline-offset-4">⬅️ 前台課表</a>
                        <a href="/admin/logout" class="text-rose-400/80 hover:text-rose-300 transition-colors underline underline-offset-4">安全登出</a>
                    </div>
                </div>
                
                <div class="overflow-x-auto rounded-xl border border-slate-800/80">
                    <table class="w-full border-collapse text-left">
                        <thead>
                            <tr class="bg-slate-950/80 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
                                <th class="px-6 py-3 font-medium">星期</th>
                                <th class="px-6 py-3 font-medium">時段</th>
                                <th class="px-4 py-3 font-medium">演出者</th>
                                <th class="px-6 py-3 text-center font-medium">席次操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            {admin_rows if admin_rows else "<tr><td colspan='4' class='text-center p-8 text-slate-500 text-sm tracking-widest'>🎵 尚無任何激盪出的樂章 (無人預約)</td></tr>"}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="w-full lg:w-80 bg-slate-900/50 backdrop-blur-md p-6 rounded-2xl shadow-xl border border-slate-800 h-fit">
                <h2 class="text-lg font-bold text-amber-400 tracking-wider mb-2">👥 演出者小節統計</h2>
                <p class="text-slate-500 text-xs mb-4 pb-2 border-b border-slate-800">監控每人 5 小節上限進度</p>
                
                <div class="rounded-xl border border-slate-800/80 overflow-hidden">
                    <table class="w-full border-collapse text-sm text-left">
                        <thead>
                            <tr class="bg-slate-950/80 text-slate-400 text-xs tracking-wider border-b border-slate-800">
                                <th class="px-4 py-2.5 font-medium">姓名</th>
                                <th class="px-4 py-2.5 text-center font-medium">已填節數</th>
                            </tr>
                        </thead>
                        <tbody>
                            {student_summary_rows if student_summary_rows else "<tr><td colspan='2' class='text-center p-6 text-slate-500 text-xs'>暫無演出者數據</td></tr>"}
                        </tbody>
                    </table>
                </div>
            </div>
            
        </div>
    </body>
    </html>
    """

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
