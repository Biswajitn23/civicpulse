import os, sqlite3, uuid
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, flash
from werkzeug.utils import secure_filename
app=Flask(__name__); app.secret_key=os.environ.get("SECRET_KEY","dev-only-change-me")
DB=os.environ.get("DATABASE_PATH","app.db"); UPLOAD=os.environ.get("UPLOAD_FOLDER","uploads"); os.makedirs(UPLOAD,exist_ok=True)
CATS=["Roads","Waste","Water","Streetlights","Drainage","Other"]; STATES=["Submitted","Acknowledged","In Progress","Resolved","Rejected"]
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
with db() as c:
 c.execute("""CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,ticket TEXT UNIQUE,category TEXT,description TEXT,address TEXT,photo TEXT,status TEXT,created TEXT)""")
 c.execute("""CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,report_id TEXT,status TEXT,note TEXT,created TEXT)""")
PAGE="""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>CivicPulse</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c1720;color:#e9f3f5;font:15px Inter,system-ui}main{max-width:1050px;margin:35px auto;padding:0 20px}.brand{font-size:24px;font-weight:850}.tag{float:right;color:#8de0c3}.hero{padding:38px 0 20px}h1{font-size:38px;letter-spacing:-1.5px;margin:12px 0}.muted{color:#9bb2ba}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{background:#142631;border:1px solid #2b414b;padding:22px;border-radius:18px;margin:15px 0}input,textarea,select{width:100%;padding:12px;margin:7px 0 13px;border-radius:9px;background:#0c1c26;color:white;border:1px solid #35515e}button,.btn{background:#73e0bb;color:#06231a;border:0;border-radius:9px;padding:11px 16px;font-weight:800;cursor:pointer;text-decoration:none;display:inline-block}.row{border-top:1px solid #304752;padding:14px 0}.status{font-size:12px;background:#23473f;color:#a7f5d8;border-radius:30px;padding:5px 9px}.flash{background:#274b4c;padding:12px;border-radius:9px;margin:10px 0}small{color:#9bb2ba}@media(max-width:700px){.grid{grid-template-columns:1fr}h1{font-size:30px}.tag{float:none;display:block;margin-top:8px}}
</style></head><body><main><div class="brand">◉ CivicPulse <span class="tag">COMMUNITY • ACTION • ACCOUNTABILITY</span></div><section class="hero"><h1>Make your neighbourhood better.</h1><p class="muted">Report local issues, track progress and make every ticket visible.</p></section>{% with m=get_flashed_messages() %}{% for x in m %}<div class="flash">{{x}}</div>{% endfor %}{% endwith %}{{body|safe}}</main></body></html>"""
@app.get("/")
def home():
 with db() as c: rows=c.execute("SELECT * FROM reports ORDER BY created DESC LIMIT 30").fetchall()
 body=render_template_string("""
 <div class="grid"><section class="card"><h2>Report an issue</h2><form method="post" action="/report">
 <label>Category</label><select name="category">{% for x in cats %}<option>{{x}}</option>{% endfor %}</select>
 <label>What happened?</label><textarea name="description" rows="4" minlength="10" required placeholder="Describe the issue clearly..."></textarea>
 <label>Location / address</label><input name="address" required placeholder="Street, area or landmark"><button>Submit report</button></form><small>Demo app: reports are stored in this app database, not sent to a municipality.</small></section>
 <section class="card"><h2>Track a ticket</h2><form action="/track"><input name="ticket" placeholder="e.g. CP-123456" required><button>Track status</button></form>
 <h2 style="margin-top:26px">Recent reports</h2>{% for r in rows %}<div class="row"><b>{{r['category']}}</b> <span class="status">{{r['status']}}</span><p>{{r['description'][:120]}}</p><small>{{r['address']}} · {{r['ticket']}}</small></div>{% else %}<p class="muted">No reports yet.</p>{% endfor %}</section></div>
 <section class="card"><h2>Demo administration</h2><p class="muted">Use the local demo queue to change report statuses. This is not production authentication.</p><a class="btn" href="/admin">Open admin queue →</a></section>
 """,cats=CATS,rows=rows)
 return render_template_string(PAGE,body=body)
@app.post("/report")
def report():
 cat=request.form.get("category","Other");desc=request.form.get("description","").strip();addr=request.form.get("address","").strip()
 if cat not in CATS or len(desc)<10 or not addr: flash("Please complete all fields.");return redirect("/")
 rid=str(uuid.uuid4());ticket="CP-"+uuid.uuid4().hex[:6].upper();now=datetime.utcnow().isoformat(timespec="minutes")
 with db() as c:
  c.execute("INSERT INTO reports VALUES(?,?,?,?,?,?,?,?)",(rid,ticket,cat,desc,addr,"","Submitted",now))
  c.execute("INSERT INTO events(report_id,status,note,created) VALUES(?,?,?,?)",(rid,"Submitted","Report received",now))
 flash("Report created. Your ticket is "+ticket);return redirect(url_for("track",ticket=ticket))
@app.get("/track")
def track():
 t=request.args.get("ticket","").strip().upper()
 with db() as c:
  r=c.execute("SELECT * FROM reports WHERE ticket=?",(t,)).fetchone()
  ev=c.execute("SELECT * FROM events WHERE report_id=? ORDER BY id",(r["id"],)).fetchall() if r else []
 body=render_template_string("""<section class="card"><a href="/" class="btn">← Home</a>{% if r %}<h2 style="margin-top:20px">{{r['ticket']}}</h2><span class="status">{{r['status']}}</span><p>{{r['description']}}</p><p class="muted">{{r['category']}} · {{r['address']}}</p><h3>Status history</h3>{% for e in ev %}<div class="row"><b>{{e['status']}}</b><p>{{e['note']}}</p><small>{{e['created']}}</small></div>{% endfor %}{% else %}<h2>Ticket not found</h2><p class="muted">Check the ticket ID and try again.</p>{% endif %}</section>""",r=r,ev=ev)
 return render_template_string(PAGE,body=body)
@app.get("/admin")
def admin():
 with db() as c: rows=c.execute("SELECT * FROM reports ORDER BY created DESC").fetchall()
 body=render_template_string("""<section class="card"><a href="/" class="btn">← Home</a><h2 style="margin-top:20px">Demo admin queue</h2><p class="muted">For demonstration only. Add real authentication and authorization before public use.</p>
 {% for r in rows %}<div class="row"><b>{{r['ticket']}} · {{r['category']}}</b><p>{{r['description']}}</p><small>{{r['address']}}</small><form method="post" action="/status/{{r['id']}}"><select name="status">{% for s in states %}<option {% if s==r['status'] %}selected{% endif %}>{{s}}</option>{% endfor %}</select><input name="note" placeholder="Update note (optional)"><button>Update status</button></form></div>{% else %}<p>No reports to manage.</p>{% endfor %}</section>""",rows=rows,states=STATES)
 return render_template_string(PAGE,body=body)
@app.post("/status/<rid>")
def status(rid):
 s=request.form.get("status");note=request.form.get("note","").strip() or "Status updated"
 if s not in STATES:return "Invalid status",400
 now=datetime.utcnow().isoformat(timespec="minutes")
 with db() as c:
  cur=c.execute("UPDATE reports SET status=? WHERE id=?",(s,rid))
  if cur.rowcount:c.execute("INSERT INTO events(report_id,status,note,created) VALUES(?,?,?,?)",(rid,s,note,now))
 flash("Status updated.");return redirect("/admin")
@app.get("/health")
def health():return {"status":"ok","app":"CivicPulse"}
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
