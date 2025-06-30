"""Main module for mapping FAQ from Gladly to Shopify"""

import re
from typing import Dict, List, Optional
from gladly_client import GladlyClient
from shopify_client import ShopifyFAQClient
from config import MAPPING_CONFIG
from rapidfuzz import fuzz, process
import json
from datetime import datetime
import pandas as pd

class FAQMapper:
    """Maps and synchronizes FAQ between Gladly and Shopify"""
    
    def __init__(self):
        self.gladly_client = GladlyClient()
        self.shopify_client = ShopifyFAQClient()
        self.config = MAPPING_CONFIG
    
    def clean_html_content(self, content: str) -> str:
        """Clean and format HTML content for Shopify"""
        if not content:
            return ""
        
        # Basic HTML cleaning - you can extend this as needed
        content = content.strip()
        
        # Ensure content is wrapped in <p> tags if not already
        if not content.startswith('<') and content:
            content = f"<p>{content}</p>"
        
        return content
    
    def generate_question_handle(self, title: str) -> str:
        """Generate a unique handle from the question title"""
        # Convert to lowercase and replace spaces/special chars with hyphens
        handle = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())
        handle = re.sub(r'\s+', '-', handle)
        handle = handle.strip('-')
        
        # Limit length
        if len(handle) > 50:
            handle = handle[:50].rstrip('-')
        
        return handle or "faq-question"
    
    def map_gladly_to_shopify_format(self, gladly_item: Dict) -> Dict:
        """Convert Gladly FAQ item to Shopify format"""
        # Extract relevant fields from Gladly item
        # Adjust these field names based on actual Gladly API response structure
        title = gladly_item.get('title', gladly_item.get('question', 'FAQ Question'))
        content = gladly_item.get('answer', gladly_item.get('content', ''))
        
        # Generate handle
        handle = self.generate_question_handle(title)
        
        # Clean content
        cleaned_content = self.clean_html_content(content)
        
        return {
            'question_handle': handle,
            'heading': title,
            'content': cleaned_content,
            'original_data': gladly_item  # Keep original for reference
        }
    
    def map_questions(self, gladly_faqs, bosapin_faqs, mapping_file):
        mapping = load_mapping(mapping_file)
        gladly_question_to_mapping = {m["gladly_question"]: m for m in mapping}
        bosapin_heading_to_mapping = {m["bosapin_heading"]: m for m in mapping}

        results = []
        for gfaq in gladly_faqs:
            m = gladly_question_to_mapping.get(gfaq["name"])
            if m:
                results.append({
                    "gladly_question": gfaq["name"],
                    "bosapin_heading": m["bosapin_heading"],
                    "bosapin_handle": m["bosapin_handle"],
                    "score": m.get("score"),
                    "updated_time": m["updated_time"]
                })
            else:
                results.append({
                    "gladly_question": gfaq["name"],
                    "bosapin_heading": None,
                    "bosapin_handle": None,
                    "score": None,
                    "updated_time": None
                })
        return results

    def get_shopify_faqs(self,bosapin_faqs):
        all_bosapin_faqs = []
        for section_id, section in bosapin_faqs["sections"].items():
            if "blocks" in section:
                category = section.get("settings", {}).get("question_category", "")
                for block_id, block in section["blocks"].items():
                    faq = dict(block["settings"])  # Copie les settings
                    faq["section_id"] = section_id
                    faq["category"] = category
                    faq["block_id"] = block_id
                    all_bosapin_faqs.append(faq)
        return all_bosapin_faqs
    
    def sync_language_faqs(self, language: str = "fr-ca", dry_run: bool = True, filter_keywords: List[str] = None, mapping_file: str = "mapping.csv") -> Dict:
        print(f"🔄 Starting FAQ sync for language: {language}")
        mapping = load_mapping(mapping_file)
        mapping_by_id = {m["gladly_id"]: m for m in mapping}

        # Get FAQ data from Gladly
        gladly_faqs = self.gladly_client.get_answers(language)
        if not gladly_faqs:
            print(f"⚠️  No FAQ data found in Gladly for {language}")
            return {"success": False, "error": "No data from Gladly"}

        # Filter by keywords if provided
        if filter_keywords:
            filtered_faqs = []
            for faq in gladly_faqs:
                title = faq.get('title', faq.get('question', '')).lower()
                content = faq.get('answer', faq.get('content', '')).lower()
                if any(keyword.lower() in title or keyword.lower() in content for keyword in filter_keywords):
                    filtered_faqs.append(faq)
            gladly_faqs = filtered_faqs
            print(f"📋 Filtered to {len(gladly_faqs)} FAQs containing keywords: {filter_keywords}")

        results = {
            "success": True,
            "language": language,
            "total_gladly_faqs": len(gladly_faqs),
            "processed": 0,
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }

        for gladly_faq in gladly_faqs:
            try:
                gladly_id = gladly_faq.get("id")
                gladly_question = gladly_faq.get("name")
                gladly_answer = gladly_faq.get("bodyHtml")
                mapping_entry = mapping_by_id.get(gladly_id)

                if mapping_entry:
                    # Compare question and answer
                    if (mapping_entry["gladly_question"] != gladly_question) or (mapping_entry["gladly_answer"] != gladly_answer):
                        if dry_run:
                            print(f"[DRY RUN] À mettre à jour: {gladly_question}")
                        else:
                            print(f"🔄 Mise à jour: {gladly_question}")
                            mapping_entry["gladly_question"] = gladly_question
                            mapping_entry["gladly_answer"] = gladly_answer
                            mapping_entry["updated_time"] = datetime.now().isoformat()
                        results["updated"] += 1
                    else:
                        print(f"⏭️  Skipping (no change): {gladly_question}")
                        results["skipped"] += 1
                else:
                    # Nouveau : ajout dans la section faq_questions_VHRPQY
                    if dry_run:
                        print(f"[DRY RUN] Would add new FAQ: {gladly_question}")
                    else:
                        print(f"➕ Ajout: {gladly_question}")
                        success = self.shopify_client.add_faq_question(
                            question_handle=self.generate_question_handle(gladly_question),
                            heading=gladly_question,
                            content=gladly_answer,
                            category=self.config.get('default_category'),
                            icon=self.config.get('default_icon'),
                            section_id='faq_questions_VHRPQY'
                        )
                        if not success:
                            results["errors"].append(f"Failed to add: {gladly_question}")
                            continue
                    # Ajout dans le mapping
                    mapping.append({
                        "gladly_id": gladly_id,
                        "bosapin_handle": "",
                        "shopify_question": gladly_question,
                        "gladly_question": gladly_question,
                        "shopify_answer": "",
                        "gladly_answer": gladly_answer,
                        "updated_time": datetime.now().isoformat()
                    })
                    results["added"] += 1
                results["processed"] += 1
            except Exception as e:
                error_msg = f"Error processing FAQ '{gladly_faq}': {str(e)}"
                print(f"❌ {error_msg}")
                results["errors"].append(error_msg)

        if not dry_run:
            save_mapping(mapping, mapping_file)

        print(f"\n📊 Sync Results for {language}:")
        print(f"   Processed: {results['processed']}")
        print(f"   Added: {results['added']}")
        print(f"   Updated: {results['updated']}")
        print(f"   Skipped: {results['skipped']}")
        print(f"   Errors: {len(results['errors'])}")

        return results
    
    def sync_all_languages(self, dry_run: bool = True, 
                          filter_keywords: List[str] = None) -> Dict:
        """Sync FAQ for all supported languages"""
        print("🌍 Starting multi-language FAQ sync")
        
        all_results = {
            "success": True,
            "languages": {},
            "total_processed": 0,
            "total_added": 0,
            "total_errors": 0
        }
        
        for language in self.gladly_client.config["supported_languages"]:
            result = self.sync_language_faqs(language, dry_run, filter_keywords)
            all_results["languages"][language] = result
            
            if result["success"]:
                all_results["total_processed"] += result["processed"]
                all_results["total_added"] += result["added"]
                all_results["total_errors"] += len(result["errors"])
            else:
                all_results["success"] = False
        
        print(f"\n🎯 Overall Sync Results:")
        print(f"   Total Processed: {all_results['total_processed']}")
        print(f"   Total Added: {all_results['total_added']}")
        print(f"   Total Errors: {all_results['total_errors']}")
        
        return all_results
    
    def search_and_sync(self, search_query: str, 
                       language: str = "fr-ca", 
                       dry_run: bool = True) -> Dict:
        """Search for specific FAQ in Gladly and sync to Shopify"""
        print(f"🔍 Searching and syncing FAQ for query: '{search_query}'")
        
        # Search in Gladly
        search_results = self.gladly_client.search_answers(search_query, language)
        
        if not search_results:
            return {"success": False, "error": "No search results found"}
        
        # Use the sync method with the search results
        # We'll temporarily replace the get_answers method result
        original_get_answers = self.gladly_client.get_answers
        self.gladly_client.get_answers = lambda lang: search_results if lang == language else []
        
        try:
            result = self.sync_language_faqs(language, dry_run)
            result["search_query"] = search_query
            return result
        finally:
            # Restore original method
            self.gladly_client.get_answers = original_get_answers

def load_mapping(mapping_file):
    df = pd.read_csv(mapping_file)
    return df.to_dict(orient="records")

def save_mapping(mapping, mapping_file):
    if not mapping:
        return
    df = pd.DataFrame(mapping)
    df.to_csv(mapping_file, index=False)

def update_mapping(mapping, gladly_question, bosapin_heading, bosapin_handle, score, gladly_id=None, shopify_question=None, shopify_answer=None, gladly_answer=None):
    from datetime import datetime
    for m in mapping:
        if m["gladly_question"] == gladly_question:
            m["bosapin_heading"] = bosapin_heading
            m["bosapin_handle"] = bosapin_handle
            m["score"] = score
            m["updated_time"] = datetime.now().isoformat()
            if gladly_id: m["gladly_id"] = gladly_id
            if shopify_question: m["shopify_question"] = shopify_question
            if shopify_answer: m["shopify_answer"] = shopify_answer
            if gladly_answer: m["gladly_answer"] = gladly_answer
            return
    # Si pas trouvé, ajoute une nouvelle entrée
    mapping.append({
        "gladly_id": gladly_id or "",
        "bosapin_handle": bosapin_handle or "",
        "shopify_question": shopify_question or bosapin_heading or "",
        "gladly_question": gladly_question or "",
        "shopify_answer": shopify_answer or "",
        "gladly_answer": gladly_answer or "",
        "updated_time": datetime.now().isoformat()
    })

if __name__ == "__main__":
    # Example usage
    mapper = FAQMapper()
    
    # Dry run sync for French
    print("=== DRY RUN SYNC ===")
    result = mapper.sync_language_faqs("fr-ca", dry_run=True)
    
    # Search and sync specific content
    #print("\n=== SEARCH AND SYNC ===")
    #search_result = mapper.search_and_sync("sapin", "fr-ca", dry_run=True)
    
    # Uncomment to perform actual sync (remove dry_run=True)
    # print("\n=== ACTUAL SYNC ===")
    # result = mapper.sync_language_faqs("fr-ca", dry_run=False)