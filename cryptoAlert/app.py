from flask import Flask, request, render_template_string, redirect, url_for
import sqlite3
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

app = Flask(__name__)

# ---------- EMAIL CREDENTIALS (from Render Environment Variables) ----------
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "chrissaaahfallah21@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "qvubuxosqkphdmio")
# -------------------------------------------------------------------------

# ---------- Database setup ----------
def init_db():
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            coin TEXT NOT NULL,
            target_price REAL NOT NULL,
            triggered INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------- Get price with 3-API fallback ----------
def get_current_price(coin):
    # 1. CoinGecko
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        return data[coin]['usd']
    except:
        pass

    # 2. Binance
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={coin.upper()}USDT"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return float(data['price'])
    except:
        pass

    # 3. CoinCap
    try:
        url = f"https://api.coincap.io/v2/assets/{coin}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return float(data['data']['priceUsd'])
    except:
        return None

# ---------- Send email ----------
def send_alert_email(email, coin, target_price, current_price):
    subject = f"🚀 {coin.capitalize()} hit ${target_price}!"
    body = f"""
    Alert triggered!

    Coin: {coin.capitalize()}
    Target: ${target_price}
    Current: ${current_price}

    Check the market now!
    """
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ---------- HTML template ----------
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crypto Alert</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; max-width: 400px; margin: 50px auto; padding: 20px; background: #f4f4f9; }
        .box { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        label { display: block; margin-top: 15px; font-weight: bold; }
        input, select { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; margin-top: 25px; background: #ff6b35; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; }
        .flash { padding: 10px; border-radius: 6px; margin-top: 10px; }
        .flash-success { background: #d4edda; color: #155724; }
        .flash-error { background: #f8d7da; color: #721c24; }
        .flash-info { background: #d1ecf1; color: #0c5460; }
        .alert-item { background: #f9f9f9; padding: 10px; border-radius: 6px; margin-bottom: 10px; }
        .status-waiting { color: orange; }
        .status-triggered { color: green; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🚀 Crypto Price Alert</h1>
        <form method="POST" action="/set_alert">
            <label>Your Email</label>
            <input type="email" name="email" placeholder="you@example.com" required>
            <label>Coin</label>
            <select name="coin">
                <option value="bitcoin">Bitcoin (BTC)</option>
                <option value="ethereum">Ethereum (ETH)</option>
            </select>
            <label>Target Price (USD)</label>
            <input type="number" step="0.01" name="price" placeholder="e.g. 70000" required>
            <button type="submit">Set Alert</button>
        </form>
        {% if message %}
        <div class="flash flash-{{ message_type }}">{{ message }}</div>
        {% endif %}
        <h3>Active Alerts</h3>
        {% for alert in alerts %}
        <div class="alert-item">
            <strong>{{ alert.coin }}</strong> at ${{ alert.target_price }}
            → <span class="{% if alert.triggered %}status-triggered{% else %}status-waiting{% endif %}">
                {% if alert.triggered %} ✅ Triggered {% else %} ⏳ Waiting {% endif %}
            </span>
            <br><small>{{ alert.email }} | {{ alert.created_at }}</small>
            <form method="POST" action="/delete/{{ alert.id }}" style="display:inline;">
                <button type="submit" style="background:#e74c3c; padding:2px 10px; width:auto; font-size:12px;">Delete</button>
            </form>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

# ---------- Routes ----------
@app.route('/')
def index():
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('SELECT id, email, coin, target_price, triggered, created_at FROM alerts ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    alerts = [{'id': r[0], 'email': r[1], 'coin': r[2], 'target_price': r[3], 'triggered': r[4], 'created_at': r[5]} for r in rows]
    return render_template_string(HTML, message="", message_type="", alerts=alerts)

@app.route('/set_alert', methods=['POST'])
def set_alert():
    email = request.form['email']
    coin = request.form['coin']
    target = float(request.form['price'])

    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('INSERT INTO alerts (email, coin, target_price) VALUES (?, ?, ?)', (email, coin, target))
    alert_id = c.lastrowid
    conn.commit()
    conn.close()

    current = get_current_price(coin)
    if current is None:
        message = "Could not fetch price, but alert saved."
        msg_type = "error"
    elif current >= target:
        if send_alert_email(email, coin, target, current):
            conn = sqlite3.connect('alerts.db')
            c = conn.cursor()
            c.execute('UPDATE alerts SET triggered = 1 WHERE id = ?', (alert_id,))
            conn.commit()
            conn.close()
            message = f"✅ Triggered! Price is ${current:.2f}. Email sent!"
            msg_type = "success"
        else:
            message = "⚠️ Price hit but email failed. Check credentials."
            msg_type = "error"
    else:
        message = f"⏳ Waiting. Current price: ${current:.2f}. Target: ${target}."
        msg_type = "info"

    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('SELECT id, email, coin, target_price, triggered, created_at FROM alerts ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    alerts = [{'id': r[0], 'email': r[1], 'coin': r[2], 'target_price': r[3], 'triggered': r[4], 'created_at': r[5]} for r in rows]
    return render_template_string(HTML, message=message, message_type=msg_type, alerts=alerts)

@app.route('/delete/<int:alert_id>', methods=['POST'])
def delete_alert(alert_id):
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('DELETE FROM alerts WHERE id = ?', (alert_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ---------- THIS IS REQUIRED FOR RENDER ----------
application = app

if __name__ == '__main__':
    app.run(debug=True)