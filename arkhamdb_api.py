import requests
from typing import Dict, List, Optional
import time

class ArkhamDBAPI:
    """Interface to the ArkhamDB API for fetching card information."""
    
    BASE_URL = "https://arkhamdb.com/api/public"
    
    def __init__(self):
        self._cards_cache: Dict[str, dict] = {}
        self._all_cards_cache: Optional[List[dict]] = None
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 500ms between requests to be extra polite
        self._session = requests.Session()  # Use session to maintain cookies
        self._browser_auth = None  # Browser authentication for cookie access
        

        
    def set_browser_auth(self, browser_auth):
        """Set the browser authentication object for cookie access."""
        self._browser_auth = browser_auth
        # Clear caches to force reload with authentication
        self._cards_cache.clear()
        self._all_cards_cache = None
        
    def _rate_limit(self):
        """Ensure we don't make requests too quickly."""
        now = time.time()
        time_since_last = now - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)
        self._last_request_time = time.time()
    
    def get_card(self, code: str) -> Optional[dict]:
        """Get card information by card code."""
        if code in self._cards_cache:
            return self._cards_cache[code]
            
        # Try all possible endpoints to get the card
        endpoints = [
            f"{self.BASE_URL}/card/{code}",  # Standard endpoint
            f"{self.BASE_URL}/card/encounter/{code}",  # Encounter card endpoint
            f"{self.BASE_URL}/card/player/{code}"  # Player card endpoint
        ]
        
        for endpoint in endpoints:
            self._rate_limit()
            try:
                headers = {
                    'User-Agent': 'TTSDeckSlicer/1.3',
                    'Accept': 'application/json'
                }
                response = requests.get(endpoint, headers=headers)
                if response.status_code == 200:
                    card = response.json()
                    self._cards_cache[code] = card
                    return card
            except Exception as e:
                pass
                continue
                
        return None

    def _ensure_cards_loaded(self) -> bool:
        """Make sure we have the full card list loaded."""
        if self._all_cards_cache is not None:
            return True
            
        self._rate_limit()
        cards = []
        
        # Try different endpoint strategies based on availability
        endpoints = [
            (f"{self.BASE_URL}/cards", "public cards"),
            # These endpoints seem to return empty responses, try alternatives
            # (f"{self.BASE_URL}/cards/encounter", "encounter cards"),
            # (f"{self.BASE_URL}/cards/player", "player cards")
        ]
        
        # If we have authentication, try the full card database endpoint
        if self._browser_auth and hasattr(self._browser_auth, 'cookies') and self._browser_auth.cookies:
            # Try authenticated endpoints that might include spoiler cards
            auth_endpoints = [
                (f"{self.BASE_URL}/cards?include_spoilers=1", "authenticated cards with spoilers"),
                ("https://arkhamdb.com/api/public/card", "all cards endpoint")  # Different base
            ]
            endpoints.extend(auth_endpoints)
        
        for endpoint, desc in endpoints:
            self._rate_limit()

            try:
                # Add browser-like headers to mimic real browser behavior
                headers = {
                    'Referer': 'https://arkhamdb.com',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br'
                }
                
                # Add authentication cookies if available
                if self._browser_auth and hasattr(self._browser_auth, 'cookies') and self._browser_auth.cookies:
                    cookie_header = '; '.join([f"{name}={value}" for name, value in self._browser_auth.cookies.items()])
                    headers['Cookie'] = cookie_header
                
                response = self._session.get(endpoint, headers=headers)
                if response.status_code == 200:
                    try:
                        endpoint_cards = response.json()
                        if isinstance(endpoint_cards, list):
                            # Only merge if we got a valid list
                            if not cards:  # First valid response
                                cards = endpoint_cards
                            else:
                                # For subsequent responses, only add new cards
                                existing_codes = {card.get('code') for card in cards}
                                cards.extend(card for card in endpoint_cards 
                                           if card.get('code') not in existing_codes)
                    except ValueError:
                        # Skip endpoints that return invalid JSON
                        continue
            except Exception:
                continue
                continue

        if cards:
            self._all_cards_cache = cards
            # Update the card cache with individual cards
            for card in self._all_cards_cache:
                if 'code' in card:
                    self._cards_cache[card['code']] = card
            return True
            
        return False
    
    def search_cards(self, query: str) -> List[dict]:
        """
        Search for cards by name, code, text, or traits.
        Returns a list of matching cards with all their information.
        """
        if not self._ensure_cards_loaded():
            return []
            
        query = query.lower()
        return [
            card for card in self._all_cards_cache
            if (query in card.get('name', '').lower() or
                query in card.get('code', '').lower() or
                query in card.get('traits', '').lower() or
                query in card.get('text', '').lower() or
                query in card.get('subname', '').lower())
        ]
    
    def get_card_name_suggestions(self, partial_name: str, limit: int = 200) -> List[dict]:
        """
        Get card name suggestions for autocomplete.
        Returns up to 200 matches by default, sorted by relevance.
        """
        results = self.search_cards(partial_name)
        # Sort by relevance - exact matches first, then startswith, then contains
        partial_name = partial_name.lower()
        def sort_key(card):
            name = card.get('name', '').lower()
            code = card.get('code', '').lower()
            subname = card.get('subname', '').lower()
            
            # Exact matches get highest priority
            if name == partial_name or code == partial_name:
                return (0, name)
            # Then names/codes that start with the query
            elif name.startswith(partial_name) or code.startswith(partial_name):
                return (1, name)
            # Then subnames that contain the query
            elif subname and partial_name in subname:
                return (2, name)
            # Then names/codes that contain the query
            elif partial_name in name or partial_name in code:
                return (3, name)
            # Finally, text/traits matches
            else:
                return (4, name)
                
        results.sort(key=sort_key)
        return results[:limit]
        
    def get_card_details(self, code: str) -> Optional[dict]:
        """
        Get detailed card information including:
        - Basic info (name, code, pack)
        - Card text and flavor
        - Game stats (cost, skills, etc)
        - Image URLs
        - Victory points, experience, etc
        """
        card = self.get_card(code)
        if not card:
            return None
            
        # Process additional data that might be useful
        details = {
            # Basic info
            'name': card.get('name', ''),
            'code': card.get('code', ''),
            'pack_name': card.get('pack_name', ''),
            'position': card.get('position'),
            'quantity': card.get('quantity'),
            
            # Card type and faction
            'type_name': card.get('type_name', ''),
            'faction_name': card.get('faction_name', ''),
            'faction2_name': card.get('faction2_name', ''),
            
            # Game text
            'text': card.get('text', ''),
            'flavor': card.get('flavor', ''),
            'traits': card.get('traits', ''),
            
            # Game stats
            'cost': card.get('cost'),
            'skill_willpower': card.get('skill_willpower'),
            'skill_intellect': card.get('skill_intellect'),
            'skill_combat': card.get('skill_combat'),
            'skill_agility': card.get('skill_agility'),
            'health': card.get('health'),
            'sanity': card.get('sanity'),
            
            # Additional info
            'subname': card.get('subname', ''),
            'illustrator': card.get('illustrator', ''),
            'victory': card.get('victory'),
            'xp': card.get('xp', 0),
            
            # Images
            'imagesrc': card.get('imagesrc', ''),
            'backimagesrc': card.get('backimagesrc', ''),
            
            # Pack info
            'pack_code': card.get('pack_code', ''),
            'cycle_name': card.get('cycle_name', '')
        }
        
        return details