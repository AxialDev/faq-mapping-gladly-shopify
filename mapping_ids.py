import requests
import json
import uuid
from datetime import datetime
import pandas as pd
import os
from config import SHOPIFY_CONFIG

# === CONFIGURATION ===
SHOPIFY_STORE = SHOPIFY_CONFIG["store_url"]
ACCESS_TOKEN = SHOPIFY_CONFIG["access_token"]
THEME_ID = SHOPIFY_CONFIG["theme_id"]
FILE_PATH = SHOPIFY_CONFIG["faq_file_path"]
API_VERSION = "2024-04"
REST_URL = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/themes/{THEME_ID}/assets.json"
HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN
}

def get_faq_data():
    params = {"asset[key]": FILE_PATH}
    response = requests.get(REST_URL, headers=HEADERS, params=params)
    response.raise_for_status()
    faq_json_str = response.json()["asset"]["value"]
    return json.loads(faq_json_str)

def backup_faq_data(faq_data):
    backup_file_path = FILE_PATH.replace(".json", f".backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    backup_payload = {
        "asset": {
            "key": backup_file_path,
            "value": json.dumps(faq_data, ensure_ascii=False)
        }
    }
    response = requests.put(REST_URL, headers=HEADERS, json=backup_payload)
    response.raise_for_status()
    print(f"✅ Sauvegarde enregistrée dans : {backup_file_path}")

def update_faq_data(faq_data):
    update_payload = {
        "asset": {
            "key": FILE_PATH,
            "value": json.dumps(faq_data, ensure_ascii=False)
        }
    }
    response = requests.put(REST_URL, headers=HEADERS, json=update_payload)
    response.raise_for_status()
    print("✅ FAQ mise à jour sur Shopify !")

def update_question_handles_to_gladly_ids(faq_data, mapping_df):
    """
    Met à jour les question_handle des questions Shopify pour utiliser les gladly_id
    """
    updates_made = 0
    
    for section_id, section in faq_data["sections"].items():
        if "blocks" in section:
            for block_id, block in section["blocks"].items():
                if block["type"] == "question":
                    current_handle = block["settings"]["question_handle"]
                    
                    # Chercher le gladly_id correspondant dans le mapping
                    matching_row = mapping_df[mapping_df["bosapin_handle"] == current_handle]
                    
                    if not matching_row.empty:
                        gladly_id = matching_row.iloc[0]["gladly_id"]
                        old_handle = current_handle
                        
                        # Mettre à jour le question_handle avec le gladly_id
                        block["settings"]["question_handle"] = gladly_id
                        
                        print(f"✅ Mis à jour: {old_handle} → {gladly_id}")
                        updates_made += 1
                    else:
                        print(f"⚠️  Pas de mapping trouvé pour: {current_handle}")
    
    print(f"\n🔄 Total des mises à jour: {updates_made}")
    return faq_data

def bulk_update_handles_from_mapping(mapping_file="mapping.csv"):
    """
    Met à jour tous les question_handle en utilisant le fichier de mapping
    """
    print("📊 Chargement du mapping...")
    mapping_df = pd.read_csv(mapping_file)
    
    print("📥 Récupération des données FAQ actuelles...")
    faq_data = get_faq_data()
    
    print("💾 Création d'une sauvegarde...")
    backup_faq_data(faq_data)
    
    print("🔄 Mise à jour des question_handle...")
    updated_faq_data = update_question_handles_to_gladly_ids(faq_data, mapping_df)
    
    print("📤 Envoi des modifications à Shopify...")
    update_faq_data(updated_faq_data)
    
    print("✅ Mise à jour terminée!")

if __name__ == "__main__":
    bulk_update_handles_from_mapping(mapping_file="mapping.csv")