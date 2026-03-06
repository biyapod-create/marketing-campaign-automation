from flask import Flask, jsonify, request, render_template_string
import sqlite3, json, os
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'whatsapp-mcp', 'whatsapp-bridge', 'store', 'messages.db')
LEADS_FILE = os.path.join(os.path.dirname(__file__), 'leads.json')
WHATSAPP_API = "http://localhost:8080/api"

STAGES = ["cold", "contacted", "replied", "call_booked", "closed"]

def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE) as f:
            return json.load(f)
    return {}

def save_leads(leads):
    with open(LEADS_FILE, 'w') as f:
        json.dump(leads, f, indent=2)

def format_ng(phone):
    phone = phone.strip().replace(" ","").replace("-","").replace("+","")
    if phone.startswith("0") and len(phone) == 11:
        phone = "234" + phone[1:]
    return phone

def get_last_message(phone):
    formatted = format_ng(phone)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT content, timestamp, is_from_me FROM messages
            WHERE chat_jid LIKE ?
            ORDER BY timestamp DESC LIMIT 1
        """, (f"%{formatted}%",))
        row = c.fetchone()
        conn.close()
        if row:
            return {"content": row[0], "timestamp": row[1], "is_from_me": bool(row[2])}
    except:
        pass
    return None

def check_for_replies(leads):
    """Auto-advance leads to 'replied' if we detect an incoming message from them."""
    changed = False
    for phone, lead in leads.items():
        if lead.get("stage") == "contacted":
            msg = get_last_message(phone)
            if msg and not msg["is_from_me"]:
                lead["stage"] = "replied"
                lead["replied_at"] = msg["timestamp"]
                lead["last_message"] = msg["content"]
                changed = True
    if changed:
        save_leads(leads)
    return leads

def get_followup_status(lead):
    """Returns: 'due', 'overdue', 'ok', 'cold'"""
    if lead.get("stage") not in ["contacted"]:
        return "ok"
    contacted_at = lead.get("contacted_at")
    if not contacted_at:
        return "ok"
    try:
        dt = datetime.fromisoformat(contacted_at)
        days_ago = (datetime.now() - dt).days
        if days_ago >= 7:
            return "cold"
        elif days_ago >= 3:
            return "overdue"
        elif days_ago >= 1:
            return "due"
        return "ok"
    except:
        return "ok"


@app.route('/api/leads', methods=['GET'])
def api_leads():
    leads = load_leads()
    leads = check_for_replies(leads)
    result = []
    for phone, lead in leads.items():
        msg = get_last_message(phone)
        followup = get_followup_status(lead)
        contacted_at = lead.get("contacted_at")
        days_since = None
        if contacted_at:
            try:
                days_since = (datetime.now() - datetime.fromisoformat(contacted_at)).days
            except: pass
        result.append({
            "phone": phone,
            "name": lead.get("name", phone),
            "business": lead.get("business", ""),
            "stage": lead.get("stage", "cold"),
            "notes": lead.get("notes", ""),
            "contacted_at": lead.get("contacted_at"),
            "replied_at": lead.get("replied_at"),
            "days_since_contact": days_since,
            "followup_status": followup,
            "last_message": msg["content"][:80] if msg else None,
            "last_from_me": msg["is_from_me"] if msg else None,
        })
    return jsonify(result)

@app.route('/api/leads', methods=['POST'])
def add_lead():
    data = request.json
    leads = load_leads()
    phone = data.get("phone", "").strip()
    if not phone:
        return jsonify({"error": "phone required"}), 400
    leads[phone] = {
        "name": data.get("name", phone),
        "business": data.get("business", ""),
        "stage": data.get("stage", "cold"),
        "notes": data.get("notes", ""),
        "contacted_at": data.get("contacted_at"),
        "replied_at": None,
        "last_message": None
    }
    save_leads(leads)
    return jsonify({"success": True})

@app.route('/api/leads/<phone>/stage', methods=['PUT'])
def update_stage(phone):
    data = request.json
    leads = load_leads()
    if phone not in leads:
        return jsonify({"error": "Lead not found"}), 404
    leads[phone]["stage"] = data.get("stage")
    if data.get("stage") == "contacted" and not leads[phone].get("contacted_at"):
        leads[phone]["contacted_at"] = datetime.now().isoformat()
    save_leads(leads)
    return jsonify({"success": True})

@app.route('/api/leads/<phone>/notes', methods=['PUT'])
def update_notes(phone):
    data = request.json
    leads = load_leads()
    if phone not in leads:
        return jsonify({"error": "Lead not found"}), 404
    leads[phone]["notes"] = data.get("notes", "")
    save_leads(leads)
    return jsonify({"success": True})

@app.route('/api/leads/<phone>', methods=['DELETE'])
def delete_lead(phone):
    leads = load_leads()
    leads.pop(phone, None)
    save_leads(leads)
    return jsonify({"success": True})

@app.route('/api/send', methods=['POST'])
def send_message():
    data = request.json
    phone = format_ng(data.get("phone", ""))
    message = data.get("message", "")
    try:
        resp = requests.post(f"{WHATSAPP_API}/send", json={"recipient": phone, "message": message}, timeout=10)
        result = resp.json()
        if result.get("success"):
            leads = load_leads()
            raw = data.get("phone")
            if raw in leads:
                leads[raw]["stage"] = "contacted"
                leads[raw]["contacted_at"] = datetime.now().isoformat()
                save_leads(leads)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/followups', methods=['GET'])
def get_followups():
    leads = load_leads()
    due = []
    for phone, lead in leads.items():
        status = get_followup_status(lead)
        if status in ["due", "overdue", "cold"]:
            due.append({"phone": phone, "name": lead.get("name"), "business": lead.get("business"), "status": status, "contacted_at": lead.get("contacted_at")})
    return jsonify(due)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    leads = load_leads()
    stats = {s: 0 for s in STAGES}
    followups_due = 0
    for lead in leads.values():
        stage = lead.get("stage", "cold")
        stats[stage] = stats.get(stage, 0) + 1
        if get_followup_status(lead) in ["due", "overdue"]:
            followups_due += 1
    stats["total"] = len(leads)
    stats["followups_due"] = followups_due
    return jsonify(stats)


HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Allennetic — Sales Pipeline</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f11; color: #e4e4e7; min-height: 100vh; }
  header { background: #18181b; border-bottom: 1px solid #27272a; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 18px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }
  header h1 span { color: #22c55e; }
  .stats { display: flex; gap: 12px; }
  .stat { background: #27272a; border-radius: 8px; padding: 8px 16px; text-align: center; }
  .stat .num { font-size: 20px; font-weight: 700; color: #fff; }
  .stat .lbl { font-size: 11px; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px; }
  .stat.alert .num { color: #f59e0b; }
  .toolbar { padding: 16px 24px; display: flex; gap: 10px; align-items: center; }
  .btn { padding: 8px 16px; border-radius: 7px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.15s; }
  .btn-primary { background: #22c55e; color: #000; }
  .btn-primary:hover { background: #16a34a; }
  .btn-sm { padding: 5px 10px; font-size: 12px; border-radius: 5px; border: none; cursor: pointer; }
  .btn-ghost { background: #27272a; color: #a1a1aa; }
  .btn-ghost:hover { background: #3f3f46; color: #fff; }
  .board { display: flex; gap: 12px; padding: 0 24px 24px; overflow-x: auto; }
  .column { flex: 0 0 260px; background: #18181b; border-radius: 10px; overflow: hidden; }
  .col-header { padding: 12px 14px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #27272a; }
  .col-title { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
  .col-count { background: #27272a; color: #a1a1aa; font-size: 11px; padding: 2px 7px; border-radius: 10px; }
  .col-cold .col-title { color: #71717a; }
  .col-contacted .col-title { color: #60a5fa; }
  .col-replied .col-title { color: #f59e0b; }
  .col-call_booked .col-title { color: #a78bfa; }
  .col-closed .col-title { color: #22c55e; }
  .cards { padding: 10px; display: flex; flex-direction: column; gap: 8px; min-height: 100px; }
  .card { background: #27272a; border-radius: 8px; padding: 12px; cursor: pointer; border: 1px solid transparent; transition: all 0.15s; position: relative; }
  .card:hover { border-color: #3f3f46; background: #2d2d30; }
  .card.selected { border-color: #22c55e; }
  .card-name { font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 2px; }
  .card-biz { font-size: 11px; color: #71717a; margin-bottom: 6px; }
  .card-msg { font-size: 11px; color: #a1a1aa; line-height: 1.4; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .card-footer { display: flex; align-items: center; justify-content: space-between; }
  .badge { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 500; }
  .badge-ok { background: #14532d; color: #86efac; }
  .badge-due { background: #713f12; color: #fde68a; }
  .badge-overdue { background: #7c2d12; color: #fdba74; }
  .badge-cold { background: #1f2937; color: #9ca3af; }
  .days { font-size: 10px; color: #52525b; }
  .panel { position: fixed; right: 0; top: 0; bottom: 0; width: 380px; background: #18181b; border-left: 1px solid #27272a; transform: translateX(100%); transition: transform 0.2s ease; overflow-y: auto; z-index: 100; }
  .panel.open { transform: translateX(0); }
  .panel-header { padding: 20px; border-bottom: 1px solid #27272a; display: flex; justify-content: space-between; align-items: center; }
  .panel-header h2 { font-size: 16px; font-weight: 600; }
  .panel-body { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .field label { display: block; font-size: 11px; color: #71717a; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px; }
  .field input, .field textarea, .field select { width: 100%; background: #27272a; border: 1px solid #3f3f46; border-radius: 6px; color: #fff; padding: 8px 10px; font-size: 13px; outline: none; }
  .field input:focus, .field textarea:focus { border-color: #22c55e; }
  .field textarea { min-height: 80px; resize: vertical; }
  .stage-select { display: flex; flex-wrap: wrap; gap: 6px; }
  .stage-btn { padding: 5px 10px; border-radius: 5px; border: 1px solid #3f3f46; background: #27272a; color: #a1a1aa; font-size: 11px; cursor: pointer; transition: all 0.15s; }
  .stage-btn.active { background: #22c55e; color: #000; border-color: #22c55e; font-weight: 600; }
  .send-box { background: #1f1f23; border-radius: 8px; padding: 14px; }
  .send-box label { font-size: 11px; color: #71717a; display: block; margin-bottom: 6px; }
  .send-box textarea { width: 100%; background: #27272a; border: 1px solid #3f3f46; border-radius: 6px; color: #fff; padding: 8px 10px; font-size: 13px; outline: none; min-height: 90px; resize: vertical; }
  .send-box textarea:focus { border-color: #22c55e; }
  .close-btn { background: none; border: none; color: #71717a; cursor: pointer; font-size: 20px; }
  .close-btn:hover { color: #fff; }
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 200; display: none; align-items: center; justify-content: center; }
  .modal-overlay.open { display: flex; }
  .modal { background: #18181b; border-radius: 12px; padding: 24px; width: 400px; border: 1px solid #27272a; }
  .modal h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
  .modal-actions { display: flex; gap: 8px; margin-top: 16px; justify-content: flex-end; }
  .toast { position: fixed; bottom: 24px; right: 24px; background: #22c55e; color: #000; padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600; opacity: 0; transition: opacity 0.3s; z-index: 300; }
  .toast.show { opacity: 1; }
  .toast.error { background: #ef4444; color: #fff; }
  .followup-banner { background: #713f12; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #fde68a; margin: 0 24px 12px; display: none; }
  .followup-banner.show { display: block; }
  @media (max-width: 600px) { .panel { width: 100%; } }
</style>
</head>
<body>
<header>
  <h1>Allennetic <span>Pipeline</span></h1>
  <div class="stats" id="stats"></div>
</header>
<div class="followup-banner" id="followupBanner"></div>
<div class="toolbar">
  <button class="btn btn-primary" onclick="openAddModal()">+ Add Lead</button>
  <button class="btn btn-ghost" onclick="loadBoard()">&#8635; Refresh</button>
</div>
<div class="board" id="board"></div>

<!-- Detail Panel -->
<div class="panel" id="panel">
  <div class="panel-header">
    <h2 id="panelName">Lead</h2>
    <button class="close-btn" onclick="closePanel()">&#x2715;</button>
  </div>
  <div class="panel-body">
    <div class="field"><label>Phone</label><input id="pPhone" readonly style="color:#71717a"/></div>
    <div class="field"><label>Business</label><input id="pBusiness" placeholder="Company name"/></div>
    <div class="field"><label>Stage</label>
      <div class="stage-select" id="stageSelect"></div>
    </div>
    <div class="field"><label>Notes</label><textarea id="pNotes" placeholder="Add notes..."></textarea></div>
    <button class="btn btn-ghost btn-sm" onclick="saveNotes()" style="align-self:flex-start">Save Notes</button>
    <div class="send-box">
      <label>Send WhatsApp Message</label>
      <textarea id="pMessage" placeholder="Type your message..."></textarea>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn btn-ghost btn-sm" onclick="loadTemplate('initial')">Initial</button>
        <button class="btn btn-ghost btn-sm" onclick="loadTemplate('followup')">Follow-up</button>
        <button class="btn btn-primary btn-sm" style="margin-left:auto" onclick="sendMessage()">Send</button>
      </div>
    </div>
    <button onclick="deleteLead()" style="background:none;border:none;color:#ef4444;font-size:12px;cursor:pointer;text-align:left">Delete lead</button>
  </div>
</div>

<!-- Add Lead Modal -->
<div class="modal-overlay" id="addModal">
  <div class="modal">
    <h2>Add New Lead</h2>
    <div class="field" style="margin-bottom:10px"><label>Name</label><input id="mName" placeholder="Contact name"/></div>
    <div class="field" style="margin-bottom:10px"><label>Business</label><input id="mBusiness" placeholder="Company / Instagram handle"/></div>
    <div class="field" style="margin-bottom:10px"><label>Phone (Nigerian format)</label><input id="mPhone" placeholder="08033001234 or 2348033001234"/></div>
    <div class="field"><label>Notes</label><textarea id="mNotes" placeholder="Where did you find them? What's the angle?" style="min-height:60px"></textarea></div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeAddModal()">Cancel</button>
      <button class="btn btn-primary" onclick="addLead()">Add Lead</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const STAGES = ["cold","contacted","replied","call_booked","closed"];
const STAGE_LABELS = {cold:"Cold",contacted:"Contacted",replied:"Replied",call_booked:"Call Booked",closed:"Closed"};
let allLeads = [];
let selectedPhone = null;

const TEMPLATES = {
  initial: "Hi, came across {business} and loved the work. We help Nigerian businesses like yours get more clients through a professional website. Worth a quick chat?",
  followup: "Hi again, just following up on my earlier message about your website. Still happy to hop on a quick call if you're open to it."
};

async function loadBoard() {
  const [leadsRes, statsRes, followupsRes] = await Promise.all([
    fetch('/api/leads').then(r=>r.json()),
    fetch('/api/stats').then(r=>r.json()),
    fetch('/api/followups').then(r=>r.json())
  ]);
  allLeads = leadsRes;
  renderStats(statsRes);
  renderBoard(leadsRes);
  renderFollowupBanner(followupsRes);
}

function renderStats(s) {
  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="num">${s.total}</div><div class="lbl">Total</div></div>
    <div class="stat"><div class="num">${s.contacted}</div><div class="lbl">Contacted</div></div>
    <div class="stat"><div class="num">${s.replied}</div><div class="lbl">Replied</div></div>
    <div class="stat"><div class="num">${s.closed}</div><div class="lbl">Closed</div></div>
    <div class="stat alert"><div class="num">${s.followups_due}</div><div class="lbl">Follow-ups Due</div></div>
  `;
}

function renderFollowupBanner(followups) {
  const banner = document.getElementById('followupBanner');
  if (followups.length === 0) { banner.classList.remove('show'); return; }
  banner.classList.add('show');
  banner.innerHTML = `&#9888; ${followups.length} lead(s) need follow-up: ${followups.map(f=>`<strong>${f.name||f.phone}</strong> (${f.status})`).join(', ')}`;
}

function renderBoard(leads) {
  const board = document.getElementById('board');
  const grouped = {};
  STAGES.forEach(s => grouped[s] = []);
  leads.forEach(l => { if (grouped[l.stage]) grouped[l.stage].push(l); });

  board.innerHTML = STAGES.map(stage => `
    <div class="column col-${stage}">
      <div class="col-header">
        <span class="col-title">${STAGE_LABELS[stage]}</span>
        <span class="col-count">${grouped[stage].length}</span>
      </div>
      <div class="cards" id="col-${stage}">
        ${grouped[stage].map(l => renderCard(l)).join('') || '<div style="color:#52525b;font-size:12px;padding:8px;text-align:center">Empty</div>'}
      </div>
    </div>
  `).join('');
}

function renderCard(l) {
  const badge = l.followup_status !== 'ok' ? `<span class="badge badge-${l.followup_status}">${l.followup_status}</span>` : '';
  const days = l.days_since_contact !== null ? `<span class="days">Day ${l.days_since_contact}</span>` : '';
  const msg = l.last_message ? `<div class="card-msg">${l.last_from_me ? '▶ ' : '◀ '}${l.last_message}</div>` : '';
  return `<div class="card ${selectedPhone===l.phone?'selected':''}" onclick="openPanel('${l.phone}')">
    <div class="card-name">${l.name}</div>
    <div class="card-biz">${l.business || l.phone}</div>
    ${msg}
    <div class="card-footer">${badge}${days}</div>
  </div>`;
}

function openPanel(phone) {
  selectedPhone = phone;
  const lead = allLeads.find(l => l.phone === phone);
  if (!lead) return;
  document.getElementById('panelName').textContent = lead.name;
  document.getElementById('pPhone').value = phone;
  document.getElementById('pBusiness').value = lead.business || '';
  document.getElementById('pNotes').value = lead.notes || '';
  document.getElementById('pMessage').value = '';
  renderStageSelect(lead.stage);
  document.getElementById('panel').classList.add('open');
}

function closePanel() {
  document.getElementById('panel').classList.remove('open');
  selectedPhone = null;
}

function renderStageSelect(current) {
  document.getElementById('stageSelect').innerHTML = STAGES.map(s =>
    `<button class="stage-btn ${s===current?'active':''}" onclick="setStage('${s}')">${STAGE_LABELS[s]}</button>`
  ).join('');
}

async function setStage(stage) {
  if (!selectedPhone) return;
  await fetch(`/api/leads/${selectedPhone}/stage`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage})});
  renderStageSelect(stage);
  showToast('Stage updated');
  loadBoard();
}

async function saveNotes() {
  if (!selectedPhone) return;
  const notes = document.getElementById('pNotes').value;
  await fetch(`/api/leads/${selectedPhone}/notes`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({notes})});
  showToast('Notes saved');
}

function loadTemplate(type) {
  const lead = allLeads.find(l => l.phone === selectedPhone);
  let msg = TEMPLATES[type];
  if (lead) msg = msg.replace('{business}', lead.business || lead.name);
  document.getElementById('pMessage').value = msg;
}

async function sendMessage() {
  const msg = document.getElementById('pMessage').value.trim();
  if (!msg || !selectedPhone) return;
  const res = await fetch('/api/send', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:selectedPhone,message:msg})});
  const data = await res.json();
  if (data.success) { showToast('Message sent!'); setStage('contacted'); document.getElementById('pMessage').value = ''; }
  else showToast('Failed: ' + data.message, true);
}

async function deleteLead() {
  if (!selectedPhone || !confirm('Delete this lead?')) return;
  await fetch(`/api/leads/${selectedPhone}`, {method:'DELETE'});
  closePanel();
  loadBoard();
  showToast('Lead deleted');
}

function openAddModal() { document.getElementById('addModal').classList.add('open'); }
function closeAddModal() { document.getElementById('addModal').classList.remove('open'); }

async function addLead() {
  const phone = document.getElementById('mPhone').value.trim();
  const name = document.getElementById('mName').value.trim();
  const business = document.getElementById('mBusiness').value.trim();
  const notes = document.getElementById('mNotes').value.trim();
  if (!phone) return showToast('Phone is required', true);
  await fetch('/api/leads', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone,name:name||phone,business,notes,stage:'cold'})});
  closeAddModal();
  loadBoard();
  showToast('Lead added');
  document.getElementById('mPhone').value=''; document.getElementById('mName').value=''; document.getElementById('mBusiness').value=''; document.getElementById('mNotes').value='';
}

function showToast(msg, isError=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (isError?' error':'');
  setTimeout(() => t.className = 'toast', 2500);
}

document.getElementById('addModal').addEventListener('click', e => { if (e.target===e.currentTarget) closeAddModal(); });
loadBoard();
setInterval(loadBoard, 30000);
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML)

if __name__ == '__main__':
    print("\\n Allennetic Pipeline Dashboard")
    print(" Open in browser: http://localhost:5050")
    print(" Press Ctrl+C to stop\\n")
    app.run(host='127.0.0.1', port=5050, debug=False)
