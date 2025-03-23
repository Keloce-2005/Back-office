import requests
import json
from django.conf import settings

def send_push_notification(user_id, title, message, url=None):
    """Envoie une notification push avec OneSignal"""
    try:
        header = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Basic {settings.ONESIGNAL_REST_API_KEY}"
        }
        
        payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            "contents": {"en": message},
            "headings": {"en": title},
            "filters": [
                {"field": "tag", "key": "user_id", "relation": "=", "value": str(user_id)}
            ]
        }
        
        if url:
            payload["url"] = url
        
        req = requests.post(
            "https://onesignal.com/api/v1/notifications",
            headers=header,
            data=json.dumps(payload)
        )
        
        return req.status_code == 200
    except Exception:
        return False