import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from rapidfuzz import fuzz
import json
from datetime import datetime
from config import SHOPIFY_CONFIG, GLADLY_CONFIG

def get_gladly_data(lng='fr-ca'):
    url = f"https://bosapin.us-1.gladly.com/api/v1/orgs/EZ_-yCNgTn6_ZVaIt_y90g/answers?lng={lng}"

    username = GLADLY_CONFIG["username"]
    api_token = GLADLY_CONFIG["api_token"]
    response = requests.get(url, auth=HTTPBasicAuth(username, api_token))

    if (response.status_code == 200):
        data = response.json()
        print("Data retrieved successfully:")
    
    return data

def get_shopify_data():
    url = f"https://{SHOPIFY_CONFIG['store_url']}/admin/api/2024-04/themes/{SHOPIFY_CONFIG['theme_id']}/assets.json"

    # === HEADERS ===
    HEADERS = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_CONFIG["access_token"]
    }

    # === 1. Récupérer le fichier existant ===
    params = {"asset[key]": SHOPIFY_CONFIG["faq_file_path"]}
    response = requests.get(url, headers=HEADERS, params=params)
    
    # Vérifier le statut de la réponse
    if response.status_code != 200:
        print(f"❌ Erreur Shopify API: {response.status_code}")
        print(f"Réponse: {response.text}")
        return None
    
    response_data = response.json()
    
    # Vérifier si la clé 'asset' existe
    if "asset" not in response_data:
        print(f"❌ Clé 'asset' manquante dans la réponse")
        print(f"Réponse complète: {response_data}")
        return None
    
    faq_json_str = response_data["asset"]["value"]
    faq_data = json.loads(faq_json_str)
    return faq_data

def create_mapping(gladly_data, shopify_data):
    all_bosapin_faqs = []
    for section_id, section in shopify_data["sections"].items():
        if "blocks" in section:
            category = section.get("settings", {}).get("question_category", "")
            for block_id, block in section["blocks"].items():
                faq = dict(block["settings"])  # Copie les settings
                faq["section_id"] = section_id
                faq["category"] = category
                faq["block_id"] = block_id
                all_bosapin_faqs.append(faq)

    mapping = []
    for gfaq in gladly_data:
        best_match = None
        best_score = 0
        for bfaq in all_bosapin_faqs:
            score = fuzz.token_sort_ratio(gfaq["name"], bfaq["heading"])
            if score > best_score:
                best_score = score
                best_match = bfaq
        if best_score > 80:  # seuil à ajuster
            mapping.append({
                "gladly_id": gfaq["id"],
                "bosapin_handle": best_match["question_handle"],
                "score": best_score,
                
            })

 
    mapdf = pd.DataFrame(mapping).merge(pd.DataFrame(all_bosapin_faqs), left_on="bosapin_handle", right_on="question_handle", how="left").merge(pd.DataFrame(gladly_data), left_on="gladly_id", right_on="id", how="left")
    return mapdf
    
if __name__ == "__main__":
    gladly_data = get_gladly_data()
    shopify_data = get_shopify_data()
    
    # Vérifier que les données ont été récupérées avec succès
    if gladly_data is None:
        print("❌ Impossible de récupérer les données Gladly")
        exit(1)
    
    if shopify_data is None:
        print("❌ Impossible de récupérer les données Shopify")
        exit(1)
    
    mapdf = create_mapping(gladly_data, shopify_data)
    
    # Créer le nom de fichier avec la date
    current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'mapping_{current_date}.csv'
    
    mapdf.to_csv(filename, index=False)
    print(f"✅ Mapping sauvegardé dans : {filename}")