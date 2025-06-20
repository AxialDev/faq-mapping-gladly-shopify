"""Client for managing FAQ in Shopify using Admin API"""

import requests
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from config import SHOPIFY_CONFIG


class ShopifyFAQClient:
    """Client to manage FAQ in Shopify theme"""
    
    def __init__(self, config: Dict = None):
        self.config = config or SHOPIFY_CONFIG
        self.store_url = self.config["store_url"]
        self.access_token = self.config["access_token"]
        self.theme_id = self.config["theme_id"]
        self.section_id = self.config["faq_section_id"]
        self.file_path = self.config["faq_file_path"]
        self.api_version = self.config["api_version"]
        
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
        
        self.rest_url = f"https://{self.store_url}/admin/api/{self.api_version}/themes/{self.theme_id}/assets.json"
    
    def get_faq_data(self) -> Optional[Dict]:
        """Retrieve current FAQ data from Shopify theme"""
        params = {"asset[key]": self.file_path}
        
        try:
            response = requests.get(self.rest_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            faq_json_str = response.json()["asset"]["value"]
            faq_data = json.loads(faq_json_str)
            
            print(f"✅ Retrieved FAQ data from Shopify")
            return faq_data
            
        except requests.RequestException as e:
            print(f"❌ Error retrieving FAQ data: {e}")
            return None
        except (KeyError, json.JSONDecodeError) as e:
            print(f"❌ Error parsing FAQ data: {e}")
            return None
    
    def backup_faq_data(self, faq_data_str: str) -> bool:
        """Create a backup of current FAQ data"""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = self.file_path.replace(".json", f".backup-{timestamp}.json")
        
        backup_payload = {
            "asset": {
                "key": backup_path,
                "value": faq_data_str
            }
        }
        
        try:
            response = requests.put(self.rest_url, headers=self.headers, json=backup_payload)
            response.raise_for_status()
            
            print(f"✅ Backup created: {backup_path}")
            return True
            
        except requests.RequestException as e:
            print(f"❌ Error creating backup: {e}")
            return False
    
    def add_faq_question(self, 
                        question_handle: str,
                        heading: str, 
                        content: str,
                        category: str = None,
                        icon: str = None,
                        section_id: str = None) -> bool:
        """Add a new FAQ question to the specified section"""
        
        # Use provided section_id or default from config
        target_section_id = section_id or self.section_id
        
        # Get current FAQ data
        faq_data = self.get_faq_data()
        if not faq_data:
            return False
        
        # Get original JSON string for backup
        faq_json_str = json.dumps(faq_data, ensure_ascii=False)
        
        # Create backup if enabled
        if self.config.get("backup_enabled", True):
            if not self.backup_faq_data(faq_json_str):
                print("⚠️  Failed to create backup, continuing anyway...")
        
        # Create new question block
        new_block_id = str(uuid.uuid4())
        new_block = {
            "type": "question",
            "settings": {
                "question_handle": question_handle,
                "heading": heading,
                "question_content": content
            }
        }
        
        # Check if section exists
        if target_section_id not in faq_data.get("sections", {}):
            print(f"❌ Section {target_section_id} not found in FAQ data")
            return False
        
        # Add the new block
        faq_data["sections"][target_section_id]["blocks"][new_block_id] = new_block
        faq_data["sections"][target_section_id]["block_order"].append(new_block_id)
        
        # Update category and icon if provided
        if category:
            faq_data["sections"][target_section_id]["settings"]["question_category"] = category
        if icon:
            faq_data["sections"][target_section_id]["settings"]["icon-faq"] = icon
        
        # Convert back to JSON and update Shopify
        updated_faq_json_str = json.dumps(faq_data, ensure_ascii=False)
        
        update_payload = {
            "asset": {
                "key": self.file_path,
                "value": updated_faq_json_str
            }
        }
        
        try:
            response = requests.put(self.rest_url, headers=self.headers, json=update_payload)
            response.raise_for_status()
            
            print(f"✅ FAQ question added successfully: {heading}")
            return True
            
        except requests.RequestException as e:
            print(f"❌ Error updating FAQ: {e}")
            return False
    
    def list_faq_questions(self, section_id: str = None) -> List[Dict]:
        """List all current FAQ questions"""
        # Use provided section_id or default from config
        target_section_id = section_id or self.section_id
        
        faq_data = self.get_faq_data()
        if not faq_data:
            return []
        
        questions = []
        
        if target_section_id in faq_data.get("sections", {}):
            section = faq_data["sections"][target_section_id]
            blocks = section.get("blocks", {})
            
            for block_id, block_data in blocks.items():
                if block_data.get("type") == "question":
                    settings = block_data.get("settings", {})
                    questions.append({
                        "id": block_id,
                        "handle": settings.get("question_handle", ""),
                        "heading": settings.get("heading", ""),
                        "content": settings.get("question_content", "")
                    })
        
        print(f"📋 Found {len(questions)} FAQ questions in section {target_section_id}")
        return questions
    
    def list_available_sections(self) -> List[str]:
        """List all available section IDs in the FAQ data"""
        faq_data = self.get_faq_data()
        if not faq_data:
            return []
        
        sections = list(faq_data.get("sections", {}).keys())
        print(f"📋 Available sections: {sections}")
        return sections
    
    def remove_faq_question(self, question_handle: str, section_id: str = None) -> bool:
        """Remove a FAQ question by its handle"""
        # Use provided section_id or default from config
        target_section_id = section_id or self.section_id
        
        faq_data = self.get_faq_data()
        if not faq_data:
            return False
        
        # Create backup
        faq_json_str = json.dumps(faq_data, ensure_ascii=False)
        if self.config.get("backup_enabled", True):
            self.backup_faq_data(faq_json_str)
        
        # Find and remove the question
        section = faq_data["sections"].get(target_section_id, {})
        blocks = section.get("blocks", {})
        block_order = section.get("block_order", [])
        
        block_to_remove = None
        for block_id, block_data in blocks.items():
            if (block_data.get("type") == "question" and 
                block_data.get("settings", {}).get("question_handle") == question_handle):
                block_to_remove = block_id
                break
        
        if not block_to_remove:
            print(f"❌ Question with handle '{question_handle}' not found in section {target_section_id}")
            return False
        
        # Remove from blocks and block_order
        del faq_data["sections"][target_section_id]["blocks"][block_to_remove]
        if block_to_remove in block_order:
            faq_data["sections"][target_section_id]["block_order"].remove(block_to_remove)
        
        # Update Shopify
        updated_faq_json_str = json.dumps(faq_data, ensure_ascii=False)
        
        update_payload = {
            "asset": {
                "key": self.file_path,
                "value": updated_faq_json_str
            }
        }
        
        try:
            response = requests.put(self.rest_url, headers=self.headers, json=update_payload)
            response.raise_for_status()
            
            print(f"✅ FAQ question removed: {question_handle}")
            return True
            
        except requests.RequestException as e:
            print(f"❌ Error removing FAQ question: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    client = ShopifyFAQClient()
    
    # List available sections
    sections = client.list_available_sections()
    
    # List current questions from default section
    questions = client.list_faq_questions()
    
    # List questions from a specific section (if you know the section ID)
    # questions_specific = client.list_faq_questions(section_id="custom-section-id")
    
    # Add a test question to default section
    client.add_faq_question(
        question_handle="test-question-2",
        heading="Question de test 2",
        content="<p>Ceci est une question de test ajoutée via l'API.</p>",
        section_id="165452516724b5285e"
    )
    
    # Add a question to a specific section
    # client.add_faq_question(
    #     question_handle="test-question-2",
    #     heading="Question spécifique",
    #     content="<p>Question ajoutée à une section spécifique.</p>",
    #     section_id="custom-section-id"
    # )