"""Client for fetching FAQ data from Gladly API"""

import requests
import pandas as pd
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional
from config import GLADLY_CONFIG


class GladlyClient:
    """Client to interact with Gladly API for FAQ data"""
    
    def __init__(self, config: Dict = None):
        self.config = config or GLADLY_CONFIG
        self.base_url = self.config["base_url"]
        self.org_id = self.config["org_id"]
        self.username = self.config["username"]
        self.api_token = self.config["api_token"]
        self.auth = HTTPBasicAuth(self.username, self.api_token)
    
    def get_answers(self, language: str = "fr-ca") -> List[Dict]:
        """Fetch all answers/FAQ from Gladly for a specific language"""
        url = f"{self.base_url}/api/v1/orgs/{self.org_id}/answers"
        params = {"lng": language}
        
        try:
            response = requests.get(url, auth=self.auth, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Retrieved {len(data)} answers for language: {language}")
            return data
            
        except requests.RequestException as e:
            print(f"❌ Error fetching answers for {language}: {e}")
            return []
    
    def search_answers(self, query: str, language: str = "fr-ca") -> List[Dict]:
        """Search for specific answers using a query"""
        url = f"{self.base_url}/api/v1/orgs/{self.org_id}/answers-search"
        params = {"q": query, "lng": language}
        
        try:
            response = requests.get(url, auth=self.auth, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Found {len(data)} answers for query '{query}' in {language}")
            return data
            
        except requests.RequestException as e:
            print(f"❌ Error searching answers: {e}")
            return []
    
    def get_all_languages_data(self) -> Dict[str, List[Dict]]:
        """Fetch FAQ data for all supported languages"""
        all_data = {}
        
        for language in self.config["supported_languages"]:
            all_data[language] = self.get_answers(language)
        
        return all_data
    
    def export_to_csv(self, data: List[Dict], filename: str) -> None:
        """Export FAQ data to CSV file"""
        if not data:
            print("⚠️  No data to export")
            return
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"📄 Data exported to {filename}")
    
    def export_all_languages_to_csv(self, output_dir: str = "data") -> None:
        """Export FAQ data for all languages to separate CSV files"""
        import os
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        all_data = self.get_all_languages_data()
        combined_data = []
        
        for language, data in all_data.items():
            if data:
                # Add language info to each record
                for item in data:
                    item['language'] = language
                
                # Export individual language file
                filename = os.path.join(output_dir, f"gladly_answers_{language.replace('-', '_')}.csv")
                self.export_to_csv(data, filename)
                
                # Add to combined data
                combined_data.extend(data)
        
        # Export combined file
        if combined_data:
            combined_filename = os.path.join(output_dir, "gladly_answers_all.csv")
            self.export_to_csv(combined_data, combined_filename)


if __name__ == "__main__":
    # Example usage
    client = GladlyClient()
    
    # Export all FAQ data
    client.export_all_languages_to_csv()
    
    # Search for specific content
    #results = client.search_answers("sapin", "fr-ca")
    #if results:
    #    client.export_to_csv(results, "data/search_results_sapin.csv")