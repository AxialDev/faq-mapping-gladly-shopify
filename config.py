"""Configuration file for FAQ mapping between Gladly and Shopify"""

# Gladly API Configuration
GLADLY_CONFIG = {
    "base_url": "https://bosapin.us-1.gladly.com",
    "org_id": "EZ_-yCNgTn6_ZVaIt_y90g", 
    "username": "performance@goaxial.com",
    "api_token": "",
    "supported_languages": ["fr-ca", "en-us"]
}

# Shopify API Configuration  
SHOPIFY_CONFIG = {
    "store_url": "bosapi-prod.myshopify.com",
    "access_token": "",
    "theme_id": "124263661620",
    "faq_section_id": "16559995512cedd4bd", 
    "faq_file_path": "templates/page.faq-questions.json",
    "api_version": "2024-04"
}

# Mapping Configuration
MAPPING_CONFIG = {
    "default_category": "Général",
    "default_icon": "bosapin-interrogation", 
    "backup_enabled": True,
    "auto_sync": False
}