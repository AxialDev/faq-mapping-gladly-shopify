# FAQ Mapping - Gladly vers Shopify

Un outil de synchronisation pour mapper et transférer les FAQ entre Gladly et Shopify.

## 📋 Description

Ce projet permet de :
1. **Récupérer** toutes les données FAQ depuis l'API Gladly
2. **Mapper** et transformer les données pour Shopify
3. **Ajouter** automatiquement les questions FAQ dans Shopify

## 🚀 Installation

1. **Cloner le repository**
```bash
git clone <repository-url>
cd faq-mapping-gladly-shopify
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Configurer les APIs**
   - Dupliquer `config.py.example` vers `config.py`
   - Remplir les credentials Gladly et Shopify

## ⚙️ Configuration

Modifiez le fichier `config.py` avec vos credentials :

```python
GLADLY_CONFIG = {
    "base_url": "https://votre-org.gladly.com",
    "org_id": "votre-org-id",
    "username": "votre-username",
    "api_token": "votre-api-token",
    "supported_languages": ["fr-ca", "en-us"]
}

SHOPIFY_CONFIG = {
    "store_url": "votre-store.myshopify.com",
    "access_token": "votre-access-token",
    "theme_id": "votre-theme-id",
    "faq_section_id": "votre-section-id",
    "faq_file_path": "sections/template-faq.json",
    "api_version": "2023-10"
}
```

## 📊 Utilisation

### Étape 1 : Récupérer les données Gladly

Exécutez le client Gladly pour télécharger toutes les FAQ dans le dossier `data/` :

```bash
python gladly_client.py
```

**Résultat :**
- `data/gladly_answers_fr_ca.csv` - FAQ en français
- `data/gladly_answers_en_us.csv` - FAQ en anglais  
- `data/gladly_answers_all.csv` - Toutes les FAQ combinées

### Étape 2 : Ajouter des questions à Shopify

#### 2.1 Lister les sections disponibles

```python
from shopify_client import ShopifyFAQClient

client = ShopifyFAQClient()

# Voir toutes les sections FAQ disponibles
sections = client.list_available_sections()
print(sections)
```

#### 2.2 Ajouter une question FAQ

```python
# Ajouter à la section par défaut (configurée dans config.py)
client.add_faq_question(
    question_handle="ma-question-1",
    heading="Comment puis-je retourner un produit ?",
    content="<p>Vous pouvez retourner votre produit dans les 30 jours...</p>"
)

# Ajouter à une section spécifique
client.add_faq_question(
    question_handle="ma-question-2", 
    heading="Quels sont les frais de livraison ?",
    content="<p>La livraison est gratuite pour les commandes de plus de 75$.</p>",
    section_id="16559995512cedd4bd"  # ID de section spécifique
)
```

#### 2.3 Lister les questions existantes

```python
# Lister toutes les questions de la section par défaut
questions = client.list_faq_questions()
for q in questions:
    print(f"- {q['heading']} (ID: {q['handle']})")

# Lister les questions d'une section spécifique  
questions_section = client.list_faq_questions(section_id="16559995512cedd4bd")
```

#### 2.4 Supprimer une question

```python
# Supprimer par handle (nom unique)
client.remove_faq_question("ma-question-1")

# Supprimer d'une section spécifique
client.remove_faq_question("ma-question-2", section_id="16559995512cedd4bd")
```

### Étape 3 : Mapper automatiquement (optionnel)

Utilisez le mapper pour transférer automatiquement depuis Gladly :

```python
from faq_mapper import FAQMapper

mapper = FAQMapper()

# Mapper toutes les FAQ français depuis les données CSV
mapper.map_gladly_to_shopify(
    csv_file="data/gladly_answers_fr_ca.csv",
    section_id="16559995512cedd4bd"
)
```

## 📁 Structure du projet

```
faq-mapping-gladly-shopify/
├── config.py              # Configuration API
├── gladly_client.py        # Client pour récupérer données Gladly
├── shopify_client.py       # Client pour ajouter FAQ à Shopify
├── faq_mapper.py          # Mapper automatique Gladly → Shopify
├── data/                  # Dossier des données exportées
│   ├── gladly_answers_fr_ca.csv
│   ├── gladly_answers_en_us.csv
│   └── gladly_answers_all.csv
└── requirements.txt       # Dépendances Python
```

## 🔧 Scripts utiles

### Récupération complète des données
```bash
python gladly_client.py
```

### Test rapide d'ajout FAQ
```python
from shopify_client import ShopifyFAQClient

client = ShopifyFAQClient()
client.add_faq_question(
    question_handle="test-question",
    heading="Question de test",
    content="<p>Ceci est un test.</p>"
)
```

### Sauvegarde automatique
Le système crée automatiquement des sauvegardes avant chaque modification dans Shopify.

## 🛠️ Dépannage

### Erreur d'authentification Gladly
- Vérifiez vos credentials dans `config.py`
- Assurez-vous que l'API token est valide

### Erreur d'authentification Shopify  
- Vérifiez votre access token
- Confirmez que le theme_id et section_id sont corrects

### Section introuvable
```python
# Lister toutes les sections disponibles
client.list_available_sections()
```

## 📝 Notes importantes

- **Sauvegarde** : Le système crée automatiquement des backups avant chaque modification
- **Langues** : Configurez les langues supportées dans `GLADLY_CONFIG`
- **Sections** : Chaque FAQ peut être ajoutée à une section Shopify spécifique
- **Handles** : Chaque question doit avoir un `question_handle` unique

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature
3. Commit vos changements  
4. Ouvrir une Pull Request
