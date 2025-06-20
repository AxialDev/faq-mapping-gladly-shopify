"""Main module for mapping FAQ from Gladly to Shopify"""

import re
from typing import Dict, List, Optional
from gladly_client import GladlyClient
from shopify_client import ShopifyFAQClient
from config import MAPPING_CONFIG


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
    
    def sync_language_faqs(self, language: str = "fr-ca", 
                          dry_run: bool = True,
                          filter_keywords: List[str] = None) -> Dict:
        """Sync FAQ from Gladly to Shopify for a specific language"""
        print(f"🔄 Starting FAQ sync for language: {language}")
        
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
                
                if any(keyword.lower() in title or keyword.lower() in content 
                      for keyword in filter_keywords):
                    filtered_faqs.append(faq)
            
            gladly_faqs = filtered_faqs
            print(f"📋 Filtered to {len(gladly_faqs)} FAQs containing keywords: {filter_keywords}")
        
        # Get current Shopify FAQ questions
        current_shopify_faqs = self.shopify_client.list_faq_questions()
        current_handles = {faq['handle'] for faq in current_shopify_faqs}
        
        results = {
            "success": True,
            "language": language,
            "total_gladly_faqs": len(gladly_faqs),
            "processed": 0,
            "added": 0,
            "skipped": 0,
            "errors": []
        }
        
        for gladly_faq in gladly_faqs:
            try:
                # Convert to Shopify format
                shopify_faq = self.map_gladly_to_shopify_format(gladly_faq)
                
                # Check if already exists
                if shopify_faq['question_handle'] in current_handles:
                    print(f"⏭️  Skipping existing FAQ: {shopify_faq['heading']}")
                    results["skipped"] += 1
                    continue
                
                if dry_run:
                    print(f"🔍 [DRY RUN] Would add FAQ: {shopify_faq['heading']}")
                else:
                    # Add to Shopify
                    success = self.shopify_client.add_faq_question(
                        question_handle=shopify_faq['question_handle'],
                        heading=shopify_faq['heading'],
                        content=shopify_faq['content'],
                        category=self.config.get('default_category'),
                        icon=self.config.get('default_icon')
                    )
                    
                    if success:
                        results["added"] += 1
                        # Add to current handles to avoid duplicates in this run
                        current_handles.add(shopify_faq['question_handle'])
                    else:
                        results["errors"].append(f"Failed to add: {shopify_faq['heading']}")
                
                results["processed"] += 1
                
            except Exception as e:
                error_msg = f"Error processing FAQ '{gladly_faq}': {str(e)}"
                print(f"❌ {error_msg}")
                results["errors"].append(error_msg)
        
        print(f"\n📊 Sync Results for {language}:")
        print(f"   Processed: {results['processed']}")
        print(f"   Added: {results['added']}")
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


if __name__ == "__main__":
    # Example usage
    mapper = FAQMapper()
    
    # Dry run sync for French
    print("=== DRY RUN SYNC ===")
    result = mapper.sync_language_faqs("fr-ca", dry_run=True)
    
    # Search and sync specific content
    print("\n=== SEARCH AND SYNC ===")
    search_result = mapper.search_and_sync("sapin", "fr-ca", dry_run=True)
    
    # Uncomment to perform actual sync (remove dry_run=True)
    # print("\n=== ACTUAL SYNC ===")
    # result = mapper.sync_language_faqs("fr-ca", dry_run=False)