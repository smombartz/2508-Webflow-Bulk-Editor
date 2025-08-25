from flask import Flask, render_template, request, jsonify
import os
import requests
import time
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class WebflowAPI:
    def __init__(self):
        self.api_token = os.getenv('WEBFLOW_API_TOKEN')
        self.base_url = 'https://api.webflow.com/v2'
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'accept': 'application/json',
            'content-type': 'application/json'
        }
        self.last_request_time = 0
        
    def _rate_limit_delay(self):
        """Implement rate limiting to respect API limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        min_delay = 1  # 1 second minimum delay between requests
        
        if time_since_last_request < min_delay:
            time.sleep(min_delay - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make authenticated API request with error handling"""
        if not self.api_token:
            logger.error("API token not configured")
            return {'success': False, 'error': 'API token not configured'}
        
        self._rate_limit_delay()
        
        url = f"{self.base_url}{endpoint}"
        
        # Log request details
        logger.info(f"Making {method} request to {url}")
        if params:
            logger.info(f"Request params: {params}")
        if data and method in ['POST', 'PATCH']:
            # Log data but truncate if too large
            data_str = json.dumps(data, indent=2)[:1000]
            if len(json.dumps(data)) > 1000:
                data_str += "... (truncated)"
            logger.info(f"Request data: {data_str}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data, timeout=30)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return {'success': False, 'error': f'Unsupported method: {method}'}
            
            # Log response details
            logger.info(f"Response status: {response.status_code}")
            
            # Check rate limit headers
            remaining = response.headers.get('X-RateLimit-Remaining')
            if remaining:
                logger.info(f"Rate limit remaining: {remaining}")
                if int(remaining) < 10:
                    logger.warning("Approaching rate limit, adding extra delay")
                    time.sleep(2)
            
            # Handle different error conditions
            if response.status_code == 401:
                error_msg = 'Invalid API token. Please check your Webflow API token.'
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            elif response.status_code == 404:
                error_msg = 'Resource not found. Please verify site/collection IDs.'
                logger.error(f"{error_msg} URL: {url}")
                return {'success': False, 'error': error_msg}
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                error_msg = f'Rate limit exceeded. Please wait {retry_after} seconds.'
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            elif response.status_code >= 400:
                try:
                    response_data = response.json()
                    error_msg = response_data.get('message', f'HTTP {response.status_code} error')
                    
                    # Log detailed error information
                    logger.error(f"API error {response.status_code}: {error_msg}")
                    logger.error(f"Full response: {json.dumps(response_data, indent=2)}")
                    
                    # Check for field-specific errors
                    if 'details' in response_data or 'errors' in response_data:
                        details = response_data.get('details', response_data.get('errors', []))
                        logger.error(f"Error details: {json.dumps(details, indent=2)}")
                        return {
                            'success': False, 
                            'error': error_msg,
                            'details': details,
                            'status_code': response.status_code
                        }
                    
                    return {
                        'success': False, 
                        'error': error_msg,
                        'status_code': response.status_code
                    }
                except:
                    error_msg = f'HTTP {response.status_code} error - could not parse response'
                    logger.error(f"{error_msg}. Raw response: {response.text[:500]}")
                    return {'success': False, 'error': error_msg}
            
            # Success case
            response_data = response.json()
            logger.info(f"Request successful. Response size: {len(json.dumps(response_data))} characters")
            return {'success': True, 'data': response_data}
            
        except requests.exceptions.Timeout:
            error_msg = 'Request timeout - Webflow API took too long to respond'
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except requests.exceptions.ConnectionError:
            error_msg = 'Connection error - Unable to reach Webflow API'
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f'Network error: {str(e)}'
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except json.JSONDecodeError:
            error_msg = 'Invalid JSON response from Webflow API'
            logger.error(f"{error_msg}. Raw response: {response.text[:500]}")
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f'Unexpected error: {str(e)}'
            logger.error(error_msg, exc_info=True)
            return {'success': False, 'error': error_msg}
    
    def get_sites(self):
        """Fetch all sites accessible to the API token"""
        return self._make_request('GET', '/sites')
    
    def get_collections(self, site_id):
        """Fetch all collections for a specific site"""
        return self._make_request('GET', f'/sites/{site_id}/collections')
    
    def get_collection_schema(self, collection_id):
        """Fetch collection schema/structure"""
        return self._make_request('GET', f'/collections/{collection_id}')
    
    def get_collection_items(self, collection_id, limit=100, offset=0):
        """Fetch collection items with pagination"""
        params = {'limit': limit, 'offset': offset}
        return self._make_request('GET', f'/collections/{collection_id}/items', params=params)
    
    def update_collection_items(self, collection_id, items_data):
        """Bulk update collection items"""
        logger.info(f"Starting bulk update for collection {collection_id} with {len(items_data)} items")
        
        # Validate items data structure
        for i, item in enumerate(items_data):
            if 'id' not in item:
                logger.error(f"Item {i} missing required 'id' field")
                return [{'success': False, 'error': f'Item {i} missing required id field'}]
            if 'fieldData' not in item:
                logger.error(f"Item {i} ({item['id']}) missing required 'fieldData' field")
                return [{'success': False, 'error': f'Item {item["id"]} missing required fieldData field'}]
        
        # Split into chunks of 100 items max per request
        chunk_size = 100
        results = []
        total_chunks = (len(items_data) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(items_data), chunk_size):
            chunk_num = (i // chunk_size) + 1
            chunk = items_data[i:i + chunk_size]
            
            logger.info(f"Processing chunk {chunk_num}/{total_chunks} with {len(chunk)} items")
            
            # Clean field data for each item in the chunk
            cleaned_chunk = []
            for item in chunk:
                cleaned_field_data = self.clean_field_data(item['fieldData'])
                if cleaned_field_data:  # Only include items with valid field data
                    cleaned_chunk.append({
                        'id': item['id'],
                        'fieldData': cleaned_field_data
                    })
                else:
                    logger.warning(f"Skipping item {item['id']} with no valid field data")
            
            if not cleaned_chunk:
                logger.warning(f"Chunk {chunk_num}/{total_chunks} has no valid items after cleaning")
                results.append({'success': True, 'message': 'No valid items to update in chunk'})
                continue
            
            # Log the first item in each chunk for debugging
            if cleaned_chunk:
                first_item = cleaned_chunk[0]
                logger.info(f"Sample item ID: {first_item['id']}")
                logger.info(f"Sample cleaned fieldData keys: {list(first_item['fieldData'].keys())}")
                logger.info(f"Sample cleaned fieldData values: {json.dumps(first_item['fieldData'], indent=2)}")
            
            chunk = cleaned_chunk  # Replace original chunk with cleaned data
            
            data = {'items': chunk}
            logger.info(f"Sending PATCH request with data: {json.dumps(data, indent=2)[:1000]}...")
            result = self._make_request('PATCH', f'/collections/{collection_id}/items', data)
            
            if result['success']:
                logger.info(f"Chunk {chunk_num}/{total_chunks} updated successfully")
            else:
                logger.error(f"Chunk {chunk_num}/{total_chunks} failed: {result['error']}")
                if 'details' in result:
                    logger.error(f"Failure details: {json.dumps(result['details'], indent=2)}")
            
            results.append(result)
            
        # Log summary
        successful_chunks = sum(1 for r in results if r['success'])
        logger.info(f"Bulk update completed: {successful_chunks}/{len(results)} chunks successful")
        
        return results
    
    def clean_field_data(self, field_data):
        """Clean and convert field data to proper types for Webflow API"""
        cleaned_data = {}
        
        for key, value in field_data.items():
            # Handle string "null" values
            if value == "null" or value == "undefined":
                logger.info(f"Skipping field {key} with string null/undefined value")
                continue  # Omit the field entirely
            
            # Handle actual None/null values
            if value is None:
                logger.info(f"Skipping field {key} with None value")
                continue  # Omit the field entirely
            
            # Handle JSON strings (like image fields)
            if isinstance(value, str):
                # Try to parse JSON strings
                if value.startswith('{') and value.endswith('}'):
                    try:
                        parsed_value = json.loads(value)
                        cleaned_data[key] = parsed_value
                        logger.info(f"Parsed JSON for field {key}")
                        continue
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON for field {key}: {value[:100]}...")
                        # Keep as string if parsing fails
                
                # Handle empty strings that should be omitted for reference fields
                if value.strip() == "" and key in ['tags', 'gallery', 'categories']:
                    logger.info(f"Skipping empty reference field {key}")
                    continue
            
            # Handle empty arrays
            if isinstance(value, list) and len(value) == 0:
                # For reference fields, omit empty arrays
                if key in ['tags', 'gallery', 'categories']:
                    logger.info(f"Skipping empty array for reference field {key}")
                    continue
            
            # Keep all other values as-is
            cleaned_data[key] = value
            
        logger.info(f"Cleaned field data: {len(field_data)} -> {len(cleaned_data)} fields")
        return cleaned_data
    
    def create_collection_items(self, collection_id, items_data):
        """Create new collection items"""
        logger.info(f"Starting bulk create for collection {collection_id} with {len(items_data)} items")
        
        # Validate items data structure
        for i, item in enumerate(items_data):
            if 'fieldData' not in item:
                logger.error(f"New item {i} missing required 'fieldData' field")
                return [{'success': False, 'error': f'New item {i} missing required fieldData field'}]
        
        # Remove temporary IDs from new items and clean field data
        clean_items = []
        for item in items_data:
            cleaned_field_data = self.clean_field_data(item['fieldData'])
            if cleaned_field_data:  # Only include items with valid field data
                clean_item = {'fieldData': cleaned_field_data}
                clean_items.append(clean_item)
            else:
                logger.warning(f"Skipping new item with no valid field data")
        
        # Split into chunks of 100 items max per request
        chunk_size = 100
        results = []
        total_chunks = (len(clean_items) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(clean_items), chunk_size):
            chunk_num = (i // chunk_size) + 1
            chunk = clean_items[i:i + chunk_size]
            
            logger.info(f"Creating chunk {chunk_num}/{total_chunks} with {len(chunk)} items")
            
            # Log the first item in each chunk for debugging
            if chunk:
                first_item = chunk[0]
                logger.info(f"Sample new item fieldData keys: {list(first_item['fieldData'].keys())}")
            
            data = {'items': chunk}
            result = self._make_request('POST', f'/collections/{collection_id}/items', data)
            
            if result['success']:
                logger.info(f"Chunk {chunk_num}/{total_chunks} created successfully")
            else:
                logger.error(f"Chunk {chunk_num}/{total_chunks} failed: {result['error']}")
                if 'details' in result:
                    logger.error(f"Failure details: {json.dumps(result['details'], indent=2)}")
            
            results.append(result)
            
        # Log summary
        successful_chunks = sum(1 for r in results if r['success'])
        logger.info(f"Bulk create completed: {successful_chunks}/{len(results)} chunks successful")
        
        return results
    
    def publish_site(self, site_id, custom_domains=None):
        """Publish site to live domains"""
        data = {
            'publishToWebflowSubdomain': True
        }
        if custom_domains:
            data['customDomains'] = custom_domains
            
        return self._make_request('POST', f'/sites/{site_id}/publish', data)

webflow_api = WebflowAPI()

@app.route('/')
def index():
    """Main bulk editor interface"""
    return render_template('index.html')

@app.route('/api/sites')
def get_sites():
    """API endpoint to fetch user's Webflow sites"""
    result = webflow_api.get_sites()
    if result['success']:
        sites = result['data'].get('sites', [])
        return jsonify({'success': True, 'sites': sites})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400

@app.route('/api/sites/<site_id>/collections')
def get_collections(site_id):
    """API endpoint to fetch collections for a site"""
    result = webflow_api.get_collections(site_id)
    if result['success']:
        collections = result['data'].get('collections', [])
        return jsonify({'success': True, 'collections': collections})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400

@app.route('/api/collections/<collection_id>')
def get_collection_schema(collection_id):
    """API endpoint to fetch collection schema"""
    result = webflow_api.get_collection_schema(collection_id)
    if result['success']:
        return jsonify({'success': True, 'collection': result['data']})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400

@app.route('/api/collections/<collection_id>/items')
def get_collection_items(collection_id):
    """API endpoint to fetch collection items with pagination"""
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    result = webflow_api.get_collection_items(collection_id, limit, offset)
    if result['success']:
        return jsonify({
            'success': True, 
            'items': result['data'].get('items', []),
            'pagination': result['data'].get('pagination', {})
        })
    else:
        return jsonify({'success': False, 'error': result['error']}), 400

@app.route('/api/collections/<collection_id>/items', methods=['POST'])
def create_collection_items(collection_id):
    """API endpoint to bulk create new collection items"""
    logger.info(f"Bulk create request received for collection: {collection_id}")
    
    data = request.get_json()
    items_data = data.get('items', [])
    
    if not items_data:
        error_msg = 'No items provided for creation'
        logger.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 400
    
    logger.info(f"Processing bulk create for {len(items_data)} new items")
    
    # Log sample of items being created (for debugging)
    if items_data:
        sample_item = items_data[0]
        logger.info(f"Sample new item structure - fieldData keys: {list(sample_item.get('fieldData', {}).keys())}")
    
    results = webflow_api.create_collection_items(collection_id, items_data)
    
    # Analyze results in detail
    successful_batches = [r for r in results if r['success']]
    failed_batches = [r for r in results if not r['success']]
    
    if failed_batches:
        # Create detailed error message
        error_details = []
        for i, batch_result in enumerate(failed_batches):
            batch_info = f"Batch {i+1}: {batch_result['error']}"
            if 'details' in batch_result:
                batch_info += f" | Details: {json.dumps(batch_result['details'])}"
            error_details.append(batch_info)
        
        detailed_error = {
            'success': False,
            'error': f'{len(failed_batches)} out of {len(results)} batches failed during creation',
            'successful_batches': len(successful_batches),
            'failed_batches': len(failed_batches),
            'error_details': error_details,
            'results': results
        }
        
        logger.error(f"Bulk create partially/completely failed: {json.dumps(detailed_error, indent=2)}")
        return jsonify(detailed_error), 400
    
    logger.info(f"Bulk create completed successfully for all {len(results)} batches")
    return jsonify({
        'success': True, 
        'message': f'Successfully created {len(items_data)} new items in {len(results)} batches',
        'results': results
    })

@app.route('/api/collections/<collection_id>/items', methods=['PATCH'])
def update_collection_items(collection_id):
    """API endpoint to bulk update collection items"""
    logger.info(f"Bulk update request received for collection: {collection_id}")
    
    data = request.get_json()
    items_data = data.get('items', [])
    
    if not items_data:
        error_msg = 'No items provided for update'
        logger.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 400
    
    logger.info(f"Processing bulk update for {len(items_data)} items")
    
    # Log sample of items being updated (for debugging)
    if items_data:
        sample_item = items_data[0]
        logger.info(f"Sample item structure - ID: {sample_item.get('id', 'MISSING')}, fieldData keys: {list(sample_item.get('fieldData', {}).keys())}")
    
    results = webflow_api.update_collection_items(collection_id, items_data)
    
    # Analyze results in detail
    successful_batches = [r for r in results if r['success']]
    failed_batches = [r for r in results if not r['success']]
    
    if failed_batches:
        # Create detailed error message
        error_details = []
        for i, batch_result in enumerate(failed_batches):
            batch_info = f"Batch {i+1}: {batch_result['error']}"
            if 'details' in batch_result:
                batch_info += f" | Details: {json.dumps(batch_result['details'])}"
            error_details.append(batch_info)
        
        detailed_error = {
            'success': False,
            'error': f'{len(failed_batches)} out of {len(results)} batches failed',
            'successful_batches': len(successful_batches),
            'failed_batches': len(failed_batches),
            'error_details': error_details,
            'results': results
        }
        
        logger.error(f"Bulk update partially/completely failed: {json.dumps(detailed_error, indent=2)}")
        return jsonify(detailed_error), 400
    
    logger.info(f"Bulk update completed successfully for all {len(results)} batches")
    return jsonify({
        'success': True, 
        'message': f'Successfully updated {len(items_data)} items in {len(results)} batches',
        'results': results
    })

@app.route('/api/sites/<site_id>/publish', methods=['POST'])
def publish_site(site_id):
    """API endpoint to publish site"""
    logger.info(f"Publish request received for site: {site_id}")
    
    try:
        data = request.get_json() or {}
        custom_domains = data.get('customDomains')
        
        logger.info(f"Publishing site {site_id} with custom_domains: {custom_domains}")
        
        result = webflow_api.publish_site(site_id, custom_domains)
        
        if result['success']:
            logger.info(f"Site {site_id} published successfully")
            return jsonify({'success': True, 'message': 'Site published successfully'})
        else:
            logger.error(f"Site {site_id} publish failed: {result['error']}")
            return jsonify({'success': False, 'error': result['error']}), 400
            
    except Exception as e:
        logger.error(f"Publish endpoint error for site {site_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': f'Server error during publish: {str(e)}'
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint to verify API token"""
    if not webflow_api.api_token:
        return jsonify({
            'success': False, 
            'error': 'API token not configured. Please add WEBFLOW_API_TOKEN to your .env file.'
        }), 400
    
    # Test API token by fetching sites
    result = webflow_api.get_sites()
    return jsonify({
        'success': result['success'],
        'error': result.get('error') if not result['success'] else None
    })

if __name__ == '__main__':
    if not os.getenv('WEBFLOW_API_TOKEN'):
        print("⚠️  Warning: WEBFLOW_API_TOKEN not found in environment variables.")
        print("   Please create a .env file with your Webflow API token.")
        print("   Example: WEBFLOW_API_TOKEN=your_token_here")
    
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )