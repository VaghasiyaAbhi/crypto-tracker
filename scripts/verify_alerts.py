import requests
import json
import sys

# Configuration
BASE_URL = "https://volusignal.com/api"
EMAIL = "savaliyaviraj5@gmail.com"
PASSWORD = "your_password_here"  # User needs to fill this in

def login():
    print(f"Logging in as {EMAIL}...")
    try:
        response = requests.post(f"{BASE_URL}/token/", json={
            "email": EMAIL,
            "password": PASSWORD
        })
        
        if response.status_code == 200:
            token = response.json().get('access')
            print("✅ Login successful!")
            return token
        else:
            print(f"❌ Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def create_alert(token, alert_type, coin_symbol="BTC", condition_value=5, time_period="1h"):
    print(f"Creating alert: {alert_type}...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "alert_type": alert_type,
        "coin_symbol": coin_symbol,
        "condition_value": condition_value,
        "time_period": time_period,
        "any_coin": False,
        "notification_channels": "email"
    }
    
    # Special handling for top_100
    if alert_type == "top_100":
        payload["coin_symbol"] = "TOP100"
        
    # Special handling for new_coin_listing
    if alert_type == "new_coin_listing":
        payload["coin_symbol"] = None
        payload["any_coin"] = True
        
    try:
        response = requests.post(f"{BASE_URL}/alerts/", headers=headers, json=payload)
        
        if response.status_code == 201:
            print(f"✅ Created {alert_type} alert successfully!")
            return True
        else:
            print(f"❌ Failed to create {alert_type}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating {alert_type}: {e}")
        return False

def main():
    if PASSWORD == "your_password_here":
        print("⚠️  Please edit this script and set your PASSWORD variable first!")
        return

    token = login()
    if not token:
        return

    alert_types = [
        "price_movement",
        "volume_change",
        "rsi_overbought",
        "rsi_oversold",
        "pump_alert",
        "dump_alert",
        "top_100",
        "new_coin_listing"
    ]
    
    success_count = 0
    for alert_type in alert_types:
        if create_alert(token, alert_type):
            success_count += 1
            
    print(f"\nSummary: {success_count}/{len(alert_types)} alerts created successfully.")

if __name__ == "__main__":
    main()
