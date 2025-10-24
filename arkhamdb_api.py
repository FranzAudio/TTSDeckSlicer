import logging
import time
import threading
from typing import Dict, List, Optional

import requests

class ArkhamDBAPI:
    """Interface to the ArkhamDB API for fetching card information."""
    
    BASE_URL = "https://arkhamdb.com/api/public"
    
    # Shared caches across all instances to avoid repeated loads
    _shared_cards_cache: Dict[str, dict] = {}
    _shared_all_cards_cache: Optional[List[dict]] = None
    _shared_search_index: List[dict] = []
    _shared_index_by_code: Dict[str, dict] = {}
    _shared_loading = False
    _cache_lock = threading.Lock()
    _logger = logging.getLogger(__name__)

    def __init__(self):
        self._cards_cache = ArkhamDBAPI._shared_cards_cache
        self._all_cards_cache = ArkhamDBAPI._shared_all_cards_cache
        self._search_index: List[dict] = ArkhamDBAPI._shared_search_index
        self._index_by_code: Dict[str, dict] = ArkhamDBAPI._shared_index_by_code
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests - reasonable for public API
        self._session = requests.Session()  # Use session to maintain cookies
        
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
            
        # Try different endpoints to get the card
        # Start with the most likely to succeed
        endpoints = [
            f"{self.BASE_URL}/card/{code}",  # Standard endpoint (should work for both player and encounter)
            f"{self.BASE_URL}/card/{code}?encounter=1",  # Explicitly request encounter cards
        ]
        
        for endpoint in endpoints:
            self._rate_limit()
            try:
                headers = {
                    'User-Agent': 'TTSDeckSlicer/1.4',
                    'Accept': 'application/json'
                }
                
                response = self._session.get(endpoint, headers=headers)
                if response.status_code == 200:
                    card = response.json()
                    self._cards_cache[code] = card
                    return card
            except Exception as e:
                continue
                
        return None

    def _ensure_cards_loaded(self) -> bool:
        """Make sure we have the full card list loaded."""
        if ArkhamDBAPI._shared_all_cards_cache is not None:
            self._sync_shared_references()
            return True

        # Acquire lock to ensure a single loader at a time
        with ArkhamDBAPI._cache_lock:
            if ArkhamDBAPI._shared_all_cards_cache is not None:
                self._sync_shared_references()
                return True
            if ArkhamDBAPI._shared_loading:
                # Another thread is already loading
                return False
            ArkhamDBAPI._shared_loading = True

        try:
            success = self._load_all_cards()
            if success:
                self._sync_shared_references()
            return success
        finally:
            with ArkhamDBAPI._cache_lock:
                ArkhamDBAPI._shared_loading = False
    
    def _load_all_cards(self) -> bool:
        """Internal method to load all cards from API."""
        self._rate_limit()
        
        # Try to get all cards in one request first (most efficient)
        try:
            headers = {
                'User-Agent': 'TTSDeckSlicer/1.4',
                'Accept': 'application/json'
            }
            
            # Try getting all cards with encounter=1 parameter - returns everything
            response = self._session.get(f"{self.BASE_URL}/cards?encounter=1", headers=headers, timeout=10)
            if response.status_code == 200:
                all_cards = response.json()
                if isinstance(all_cards, list) and len(all_cards) > 0:
                    self._set_shared_data(all_cards)
                    print(f"Loaded {len(all_cards)} cards from ArkhamDB")
                    return True
        except Exception as e:
            print(f"Failed to load all cards: {e}")
        
        # Fallback: try separate endpoints
        self._rate_limit()
        cards = []
        
        endpoints = [
            (f"{self.BASE_URL}/cards", "player cards"),
            (f"{self.BASE_URL}/cards?encounter=1", "encounter cards"),
        ]
        
        for endpoint, desc in endpoints:
            self._rate_limit()
            try:
                headers = {
                    'User-Agent': 'TTSDeckSlicer/1.4',
                    'Accept': 'application/json'
                }
                
                response = self._session.get(endpoint, headers=headers, timeout=10)
                if response.status_code == 200:
                    try:
                        endpoint_cards = response.json()
                        if isinstance(endpoint_cards, list):
                            if not cards:  # First valid response
                                cards = endpoint_cards
                            else:
                                # For subsequent responses, only add new cards
                                existing_codes = {card.get('code') for card in cards}
                                cards.extend(card for card in endpoint_cards 
                                           if card.get('code') not in existing_codes)
                    except ValueError:
                        continue
            except Exception:
                continue

        if cards:
            self._set_shared_data(cards)
            print(f"Loaded {len(cards)} cards from ArkhamDB")
            return True
            
        return False
    
    def _set_shared_data(self, cards: List[dict]):
        """Update shared caches and search index with freshly loaded data."""
        search_index = self._build_search_index(cards)
        with ArkhamDBAPI._cache_lock:
            ArkhamDBAPI._shared_all_cards_cache = cards
            ArkhamDBAPI._shared_cards_cache = {
                card['code']: card for card in cards if card.get('code')
            }
            ArkhamDBAPI._shared_search_index = search_index
            ArkhamDBAPI._shared_index_by_code = {
                entry['card'].get('code'): entry
                for entry in search_index
                if entry['card'].get('code')
            }
        self._sync_shared_references()

    def _sync_shared_references(self):
        """Sync instance references with shared caches."""
        self._all_cards_cache = ArkhamDBAPI._shared_all_cards_cache
        self._cards_cache = ArkhamDBAPI._shared_cards_cache
        self._search_index = ArkhamDBAPI._shared_search_index
        self._index_by_code = ArkhamDBAPI._shared_index_by_code

    def _build_search_index(self, cards: List[dict]) -> List[dict]:
        """Create a pre-normalized index to speed up searches."""
        index: List[dict] = []
        for card in cards:
            entry = {
                'card': card,
                'name': (card.get('name') or '').lower(),
                'code': (card.get('code') or '').lower(),
                'subname': (card.get('subname') or '').lower(),
                'traits': (card.get('traits') or '').lower(),
                'text': (card.get('text') or '').lower(),
                'is_encounter': self._is_encounter_card(card),
            }
            index.append(entry)
        return index

    def search_cards(self, query: str, limit: Optional[int] = None, include_encounter: bool = True) -> List[dict]:
        """Search for cards by relevance with optional limit."""
        if not self._ensure_cards_loaded():
            return []

        index = self._search_index or []
        if not index:
            return []

        query = (query or "").strip().lower()
        if not query:
            return []

        if not limit or limit <= 0:
            limit = len(index)
        include_text = len(query) >= 3

        exact_matches: List[dict] = []
        prefix_matches: List[dict] = []
        subname_matches: List[dict] = []
        contains_matches: List[dict] = []
        traits_matches: List[dict] = []
        text_matches: List[dict] = []

        scanned = 0
        start_time = time.perf_counter()
        total = 0

        for entry in index:
            if not include_encounter and entry['is_encounter']:
                continue

            card = entry['card']
            name = entry['name']
            code = entry['code']
            subname = entry['subname']
            traits = entry['traits']
            text = entry['text']

            scanned += 1

            if query == name or query == code:
                exact_matches.append(card)
                total += 1
            elif name.startswith(query) or code.startswith(query):
                prefix_matches.append(card)
                total += 1
            elif subname and (subname == query or subname.startswith(query)):
                subname_matches.append(card)
                total += 1
            elif (query in name or query in code or (subname and query in subname)):
                contains_matches.append(card)
                total += 1
            elif traits and query in traits:
                traits_matches.append(card)
                total += 1
            elif (include_text and total < limit and text and query in text):
                text_matches.append(card)
                total += 1
            else:
                continue

            if total >= limit:
                break

        combined = (exact_matches + prefix_matches + subname_matches +
                    contains_matches + traits_matches + text_matches)
        if limit and len(combined) > limit:
            combined = combined[:limit]

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        log_level = logging.INFO if duration_ms > 50 else logging.DEBUG
        ArkhamDBAPI._logger.log(
            log_level,
            "search_cards query='%s' matches=%d scanned=%d limit=%d duration=%.1fms",
            query,
            len(combined),
            scanned,
            limit,
            duration_ms,
        )
        return combined
    
    def get_card_name_suggestions(self, partial_name: str, limit: int = 200, include_encounter: bool = True) -> List[dict]:
        """
        Get card name suggestions for autocomplete.
        Returns up to 200 matches by default, sorted by relevance.
        
        Args:
            partial_name: The partial name to search for
            limit: Maximum number of results to return
            include_encounter: Whether to include encounter cards in results
        """
        results = self.search_cards(partial_name, limit=limit, include_encounter=include_encounter)
        return results[:limit]
    
    def _is_encounter_card(self, card: dict) -> bool:
        """Check if a card is an encounter card."""
        # Encounter cards typically have different faction codes or types
        faction = card.get('faction_code', '')
        type_code = card.get('type_code', '')
        
        # Common encounter card indicators
        encounter_factions = ['mythos', 'neutral']  # Common encounter factions
        encounter_types = ['enemy', 'treachery', 'location', 'agenda', 'act', 'scenario']
        
        return (faction in encounter_factions and type_code in encounter_types) or \
               card.get('encounter_code') is not None or \
               card.get('encounter_position') is not None
        
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