import os
import psutil
import requests
import json
from datetime import datetime
from lg_logger import logger

class HardwareMonitor:
    @staticmethod
    def get_stats():
        """Fetches CPU, RAM, and Temperature data."""
        try:
            cpu_usage = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            
            # Raspberry Pi Temperature
            temp = "N/A"
            temp_path = "/sys/class/thermal/thermal_zone0/temp"
            if os.path.exists(temp_path):
                with open(temp_path, "r") as f:
                    temp = round(int(f.read()) / 1000, 1)
            
            return {
                "cpu": cpu_usage,
                "ram_used": round(ram.used / (1024**2), 1),
                "ram_total": round(ram.total / (1024**2), 1),
                "ram_pct": ram.percent,
                "temp": temp
            }
        except Exception as e:
            logger.error(f"Error fetching hardware stats: {e}")
            return None

class DiscordNotifier:
    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1495892313854054551/rlhrCxzkdY_ocM57iSYqePgMXbDbW_mNiyH71Yw9xSkUDYELGBFnafBNqkMCuXzk0Ede")
        self.session = requests.Session()

    def send_embed(self, title, description, color=0x3498db, fields=None):
        """
        Sends a rich embed to Discord.
        Colors: Success=0x2ecc71, Error=0xe74c3c, Info=0x3498db, Heartbeat=0x95a5a6
        """
        if not self.webhook_url:
            return

        payload = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {"text": "LGVoter Raspberry Pi Monitor"},
                "fields": fields or []
            }]
        }

        try:
            response = self.session.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")

    def notify_success(self, site_name, result_msg):
        fields = [{"name": "Site", "value": site_name, "inline": True}]
        self.send_embed(
            title="✅ Vote Réussi",
            description=result_msg,
            color=0x2ecc71,
            fields=fields
        )

    def notify_error(self, stage, error_msg, hardware_stats=None):
        fields = [{"name": "Etape", "value": stage, "inline": False}]
        if hardware_stats:
            fields.append({
                "name": "Hardware Stack",
                "value": f"CPU: {hardware_stats['cpu']}% | RAM: {hardware_stats['ram_pct']}% | Temp: {hardware_stats['temp']}°C",
                "inline": False
            })
        
        self.send_embed(
            title="⚠️ Erreur Critique / Blocage",
            description=error_msg,
            color=0xe74c3c,
            fields=fields
        )

    def notify_heartbeat(self, stats, state_summary):
        fields = [
            {"name": "CPU", "value": f"{stats['cpu']}%", "inline": True},
            {"name": "RAM", "value": f"{stats['ram_pct']}%", "inline": True},
            {"name": "Temp", "value": f"{stats['temp']}°C", "inline": True},
            {"name": "Status", "value": state_summary, "inline": False}
        ]
        self.send_embed(
            title="💓 Heartbeat - System OK",
            description="Le bot est toujours actif et surveille les votes.",
            color=0x95a5a6,
            fields=fields
        )

    def notify_status_summary(self, timers_info):
        """
        Sends a summary of all site timers to Discord.
        """
        fields = []
        for site, wait_info in timers_info.items():
            fields.append({
                "name": f"📍 {site}",
                "value": wait_info,
                "inline": False
            })
        
        self.send_embed(
            title="📊 Résumé de l'État des Votes",
            description="Voici le compte à rebours pour chaque site de vote.",
            color=0xf1c40f, # Yellow/Gold
            fields=fields
        )

# Singletons
monitor = HardwareMonitor()
notifier = DiscordNotifier()
