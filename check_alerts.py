import sqlite3
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------- YOUR EMAIL CREDENTIALS (SAME AS IN app.py) ----------
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"
# ----------------------------------------------------------------

def get_current_price(coin):
    """Try multiple APIs to get the current price."""
    # 1. CoinGecko with user-agent
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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

def get_waiting_alerts():
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('SELECT id, email, coin, target_price FROM alerts WHERE triggered = 0')
    rows = c.fetchall()
    conn.close()
    return rows

def mark_triggered(alert_id):
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('UPDATE alerts SET triggered = 1 WHERE id = ?', (alert_id,))
    conn.commit()
    conn.close()

def send_alert(email, coin, target_price, current_price):
    subject = f"🚀 {coin.capitalize()} hit ${target_price}!"
    body = f"""
    Your alert has been triggered!

    Coin: {coin.capitalize()}
    Target price: ${target_price}
    Current price: ${current_price}

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
        print(f"Failed to send to {email}: {e}")
        return False

def check_all():
    alerts = get_waiting_alerts()
    if not alerts:
        print("No waiting alerts.")
        return
    
    for alert_id, email, coin, target in alerts:
        current = get_current_price(coin)
        if current is None:
            print(f"Could not fetch price for {coin}, skipping.")
            continue
        
        print(f"Checking {coin}: target ${target}, current ${current:.2f}")
        
        if current >= target:
            print(f"Triggering alert for {email}")
            success = send_alert(email, coin, target, current)
            if success:
                mark_triggered(alert_id)
                print(f"Alert {alert_id} marked as triggered.")
            else:
                print(f"Email failed, will retry next hour.")

if __name__ == '__main__':
    check_all()