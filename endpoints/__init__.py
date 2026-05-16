from flask import Blueprint, request, jsonify
import requests
import os
from datetime import datetime

check_cosmetic_bp = Blueprint('check_cosmetic', __name__)

# ================== CONFIG ==================
PLAYFAB_TITLE_ID = "19F7B9"          # ← CHANGE THIS
PLAYFAB_SECRET_KEY = os.getenv("AKC8FPQKWT1QQ8YX74N8KQ56U6RXUUUWXFNEOH54T8UC38WKNN")

# Discord Webhook
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1505311268087533568/mi_LO15k5cwimVgr4F6JsvdLNA8rOz8g2o3p6SjZZAGOIU860WfUiytj26OEXHGSilTD"  # ← CHANGE THIS

COSMETIC_ID = "LBAAD."
# ===========================================

def send_to_discord(found_players, total_checked):
    if not found_players:
        return

    players_text = "\n".join([
        f"**{p['displayName']}** (`{p['playFabId']}`)" for p in found_players
    ])

    embed = {
        "title": "🎨 LBAAD. Cosmetic Found!",
        "color": 0xFF00FF,
        "description": players_text,
        "fields": [
            {"name": "Total Checked", "value": str(total_checked), "inline": True},
            {"name": "Found", "value": str(len(found_players)), "inline": True},
            {"name": "Cosmetic", "value": COSMETIC_ID, "inline": True}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

    payload = {
        "content": "**LBAAD. Detection Report**",
        "embeds": [embed]
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except:
        pass  # Fail silently


@check_cosmetic_bp.route('/api/check-cosmetic', methods=['POST'])
def check_cosmetic():
    data = request.get_json(silent=True) or {}
    player_ids = data.get("playerIds", [])

    if not player_ids or not isinstance(player_ids, list):
        return jsonify({"error": "playerIds array is required"}), 400

    if len(player_ids) > 150:
        return jsonify({"error": "Too many players (max 150)"}), 400

    results = []
    found_players = []

    headers = {
        "X-SecretKey": PLAYFAB_SECRET_KEY,
        "Content-Type": "application/json"
    }

    for pid in player_ids:
        try:
            # Get Inventory
            inv_resp = requests.post(
                f"https://{PLAYFAB_TITLE_ID}.playfabapi.com/Server/GetUserInventory",
                json={"PlayFabId": pid},
                headers=headers,
                timeout=10
            )

            has_cosmetic = False
            display_name = "Unknown"

            if inv_resp.status_code == 200:
                inventory = inv_resp.json().get("data", {}).get("Inventory", [])
                for item in inventory:
                    if item.get("ItemId") == COSMETIC_ID:
                        has_cosmetic = True
                        break

            # Get Display Name
            try:
                profile_resp = requests.post(
                    f"https://{PLAYFAB_TITLE_ID}.playfabapi.com/Server/GetPlayerProfile",
                    json={"PlayFabId": pid, "ProfileConstraints": {"ShowDisplayName": True}},
                    headers=headers,
                    timeout=8
                )
                if profile_resp.status_code == 200:
                    display_name = profile_resp.json().get("data", {}).get("PlayerProfile", {}).get("DisplayName", "Unknown")
            except:
                pass

            result = {
                "playFabId": pid,
                "displayName": display_name,
                "hasLBAAD": has_cosmetic
            }
            results.append(result)

            if has_cosmetic:
                found_players.append(result)

        except Exception as e:
            results.append({"playFabId": pid, "error": str(e), "hasLBAAD": False})

    # Send to Discord if anyone has the cosmetic
    if found_players:
        send_to_discord(found_players, len(player_ids))

    return jsonify({
        "success": True,
        "totalChecked": len(player_ids),
        "found": len(found_players),
        "results": results
    })
