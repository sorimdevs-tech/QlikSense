import os
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv
import json

load_dotenv()

class QlikClient:
    def __init__(self):
        self.api_key = os.getenv('QLIK_API_KEY')
        self.tenant_url = os.getenv('QLIK_TENANT_URL')
        self.api_base_url = os.getenv('QLIK_API_BASE_URL')
        
        # Use tenant-specific API URL
        if not self.api_base_url and self.tenant_url:
            self.api_base_url = f"{self.tenant_url}/api/v1"
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if not self.api_key:
            raise ValueError('QLIK_API_KEY is not set in environment variables')
        if not self.api_base_url:
            raise ValueError('QLIK_API_BASE_URL or QLIK_TENANT_URL is not set in environment variables')

    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Qlik Cloud"""
        url = f'{self.api_base_url}/users/me'
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            print(f"Connection test - Status: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.exceptions.RequestException as e:
            print(f"Connection test failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_applications(self) -> List[Dict[str, Any]]:
        """Retrieve list of all applications"""
        url = f'{self.api_base_url}/apps'
        try:
            print(f"Fetching apps from: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            print(f"Apps response status: {response.status_code}")
            print(f"Apps response: {response.text}")
            response.raise_for_status()
            
            data = response.json()
            # Handle different response formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            elif isinstance(data, dict) and 'items' in data:
                return data['items']
            else:
                return [data] if data else []
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching applications: {str(e)}")
            return []

    def get_application_details(self, app_id: str) -> Dict[str, Any]:
        """Get details of a specific application"""
        url = f'{self.api_base_url}/apps/{app_id}'
        try:
            print(f"Fetching app details from: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            print(f"App details response status: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching application details: {str(e)}")
            return {"error": str(e)}

    def get_application_data(self, app_id: str) -> Dict[str, Any]:
        """Fetch data from a specific application using evaluation API"""
        # Try different endpoints for getting app data
        endpoints_to_try = [
            f'{self.api_base_url}/apps/{app_id}/data/metadata',
            f'{self.api_base_url}/apps/{app_id}/evaluation/data',
            f'{self.api_base_url}/apps/{app_id}/objects'
        ]
        
        for url in endpoints_to_try:
            try:
                print(f"Trying to fetch app data from: {url}")
                response = requests.get(url, headers=self.headers, timeout=10)
                print(f"Data response status: {response.status_code}")
                if response.status_code == 200:
                    return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error with endpoint {url}: {str(e)}")
                continue
        
        return {"error": "Could not retrieve application data from any endpoint"}

    def get_applications_with_details(self) -> List[Dict[str, Any]]:
        """Get applications with their details"""
        apps = self.get_applications()
        for app in apps:
            app_id = app.get('id') or app.get('qDocId')
            if app_id:
                try:
                    details = self.get_application_details(app_id)
                    app['details'] = details
                except Exception as e:
                    app['details'] = {'error': str(e)}
        return apps

    def get_spaces(self) -> List[Dict[str, Any]]:
        """Get list of spaces"""
        url = f'{self.api_base_url}/spaces'
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('data', []) if isinstance(data, dict) else data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching spaces: {str(e)}")
            return []
