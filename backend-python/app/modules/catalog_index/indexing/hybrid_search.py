"""
Hybrid Search - Combines BM25 and Vector Search

Uses Reciprocal Rank Fusion (RRF) to merge results with enhanced phrase matching.
Enhanced with smarter category detection and fallback strategies.
"""

from typing import List, Dict, Any, Optional, Tuple
import re

from .bm25_index import BM25Index
from .vector_index import VectorIndex


class HybridSearch:
    """Combines BM25 and Vector search using RRF with phrase boost"""
    
    # Common product nouns that should match in title - ALL CATEGORIES
    IMPORTANT_NOUNS = {
        # Office Furniture
        'chair', 'chairs', 'desk', 'desks', 'table', 'tables', 'cabinet', 'cabinets',
        'shelf', 'shelves', 'bookcase', 'bookcases', 'pedestal', 'pedestals',
        'credenza', 'workstation', 'workstations', 'pod', 'pods', 'screen', 'screens',
        # Hospitality Furniture
        'stool', 'stools', 'sofa', 'sofas', 'lounge', 'lounges', 'ottoman', 'ottomans',
        # Home Furniture
        'bed', 'beds', 'mattress', 'mattresses', 'wardrobe', 'wardrobes', 'dresser', 'dressers',
        'nightstand', 'nightstands', 'drawer', 'drawers', 'recliner', 'recliners',
        # Sports & Fitness - Cardio
        'treadmill', 'treadmills', 'bike', 'bikes', 'rower', 'rowers', 'elliptical',
        # Sports & Fitness - Weights
        'dumbbell', 'dumbbells', 'kettlebell', 'kettlebells', 'barbell', 'barbells',
        'plate', 'plates', 'weight', 'weights', 'rack', 'racks',
        # Sports & Fitness - Gym Equipment
        'bench', 'benches', 'mat', 'mats', 'trampoline', 'trampolines', 'ball', 'balls',
        # Boxing & MMA
        'gloves', 'glove', 'bag', 'bags', 'pad', 'pads', 'shield', 'shields',
        'protector', 'protectors', 'guard', 'guards', 'wrap', 'wraps', 'ring', 'rings',
        # Martial Arts
        'uniform', 'uniforms', 'belt', 'belts', 'weapon', 'weapons', 'nunchaku', 'bo',
        # Functional Fitness & Yoga/Relaxation
        'rope', 'ropes', 'band', 'bands', 'roller', 'rollers', 'slider', 'sliders',
        'yoga', 'pilates', 'massage', 'relaxation', 'stretching', 'flexibility',
        # Pet Products - Dogs
        'kennel', 'kennels', 'crate', 'crates', 'pram', 'prams', 'collar', 'collars',
        'leash', 'leashes', 'lead', 'leads', 'toy', 'toys',
        # Pet Products - Cats
        'tree', 'trees', 'litter', 'carrier', 'carriers', 'scratcher', 'scratchers',
        # Pet Products - Other
        'cage', 'cages', 'aviary', 'aviaries', 'hutch', 'hutches', 'coop', 'coops',
        # Pet Products - Aquarium
        'aquarium', 'aquariums', 'tank', 'tanks', 'pump', 'pumps', 'filter', 'filters',
        'bowl', 'bowls', 'feeder', 'feeders', 'fountain', 'fountains',
        # Electric Scooters
        'scooter', 'scooters', 'wheel', 'wheels', 'tire', 'tires', 'battery', 'batteries',
    }
    
    # Category mapping for filtering - COMPREHENSIVE for all product types
    CATEGORY_KEYWORDS = {
        # ============ SPORTS & FITNESS ============
        # Fitness Accessories & Equipment
        'fitness': ['fitness', 'workout', 'exercise', 'training', 'gym', 'fitness accessories'],
        'treadmill': ['treadmill', 'treadmills', 'running machine', 'walking machine', 'cardio'],
        'exercise bike': ['exercise bike', 'exercise bikes', 'spin bike', 'stationary bike', 'cycling bike', 'indoor bike', 'recumbent bike'],
        'rowing': ['rowing', 'rowing machine', 'rowing machines', 'rower', 'rowers', 'erg', 'ergometer'],
        'dumbbell': ['dumbbell', 'dumbbells', 'dumb bell', 'free weights', 'hand weights'],
        'kettlebell': ['kettlebell', 'kettlebells', 'kettle bell', 'kb', 'cast iron kettlebell'],
        'gym bench': ['gym bench', 'weight bench', 'workout bench', 'adjustable bench', 'flat bench', 'incline bench', 'decline bench'],
        'air track': ['air track', 'air track mat', 'tumbling mat', 'gymnastics mat', 'inflatable mat'],
        'trampoline': ['trampoline', 'trampolines', 'rebounder', 'mini trampoline', 'fitness trampoline'],
        
        # Boxing & Muay Thai
        'boxing': ['boxing', 'boxer', 'punching', 'muay thai', 'kickboxing', 'boxing training'],
        'boxing gloves': ['boxing gloves', 'sparring gloves', 'training gloves', 'bag gloves', 'fight gloves'],
        'boxing bag': ['boxing bag', 'punching bag', 'heavy bag', 'speed bag', 'kick bag', 'uppercut bag', 'free standing bag'],
        'focus pads': ['focus pads', 'punch mitts', 'focus mitts', 'target pads', 'coaching pads'],
        'kick shields': ['kick shields', 'kick pads', 'thai pads', 'curved kick shield', 'belly pad'],
        'boxing ring': ['boxing ring', 'boxing rings', 'fight ring', 'mma cage'],
        'boxing apparel': ['boxing shorts', 'boxing shoes', 'boxing boots', 'hand wraps', 'inner gloves', 'carry bag'],
        'protective equipment': ['headgear', 'head guard', 'body protector', 'chest guard', 'groin guard', 'shin guards', 'mouth guard'],
        
        # Martial Arts
        'martial arts': ['martial arts', 'karate', 'taekwondo', 'judo', 'jiu jitsu', 'bjj', 'kung fu', 'aikido'],
        'martial arts uniform': ['gi', 'uniform', 'dobok', 'karate gi', 'judo gi', 'bjj gi', 'martial arts belt'],
        'training weapons': ['training weapons', 'bo staff', 'nunchaku', 'practice sword', 'training knife', 'kali sticks', 'escrima'],
        'martial arts protective': ['sparring gear', 'chest protector', 'arm guards', 'leg guards', 'instep guards'],
        
        # Functional Fitness
        'functional fitness': ['functional fitness', 'crossfit', 'hiit', 'circuit training'],
        'strength equipment': ['strength equipment', 'power rack', 'squat rack', 'pull up bar', 'dip station', 'cable machine'],
        'conditioning': ['conditioning', 'battle ropes', 'slam ball', 'medicine ball', 'plyo box', 'sandbag'],
        'speed agility': ['speed', 'agility', 'agility ladder', 'cones', 'hurdles', 'speed parachute'],
        'body weight': ['body weight', 'resistance bands', 'suspension trainer', 'trx', 'parallettes', 'ab roller'],
        'mobility recovery': ['mobility', 'recovery', 'foam roller', 'massage ball', 'yoga block', 'stretch strap', 'lacrosse ball'],
        
        # Yoga & Relaxation
        'yoga': ['yoga', 'yoga mat', 'yoga mats', 'yoga block', 'yoga strap', 'yoga wheel', 'yoga bolster', 'meditation'],
        'massage': ['massage', 'massage gun', 'massage roller', 'massage ball', 'relaxation', 'muscle recovery'],
        'pilates': ['pilates', 'pilates ring', 'pilates ball', 'pilates mat', 'reformer'],
        'stretching': ['stretching', 'stretch', 'flexibility', 'stretch strap', 'stretch band'],
        
        # Weightlifting
        'weightlifting': ['weightlifting', 'weight lifting', 'powerlifting', 'olympic lifting', 'strength training'],
        'barbell': ['barbell', 'barbells', 'olympic barbell', 'ez curl bar', 'trap bar', 'barbell rack'],
        'weight plates': ['weight plates', 'olympic plates', 'bumper plates', 'iron plates', 'rubber plates', 'fractional plates'],
        
        # MMA
        'mma': ['mma', 'mixed martial arts', 'ufc', 'cage fighting', 'grappling', 'ground and pound'],
        'mma gloves': ['mma gloves', 'grappling gloves', 'hybrid gloves', 'sparring mma gloves'],
        'mma shorts': ['mma shorts', 'fight shorts', 'grappling shorts', 'vale tudo shorts'],
        'rashguard': ['rashguard', 'rash guard', 'compression shirt', 'bjj rashguard'],
        
        # Rugby
        'rugby': ['rugby', 'rugby ball', 'rugby balls', 'rugby training', 'tackle bag', 'scrum machine', 'rugby pad'],
        
        # Basketball
        'basketball': ['basketball', 'basketball hoop', 'basketball ring', 'basketball stand', 'basketball accessories'],
        
        # ============ ELECTRIC SCOOTERS ============
        'scooter': ['scooter', 'scooters', 'electric scooter', 'e-scooter', 'escooter', 'kick scooter', 'commuter scooter'],
        'scooter accessories': ['scooter accessories', 'scooter helmet', 'scooter bag', 'scooter lock', 'scooter tire', 'scooter battery'],
        
        # ============ OFFICE FURNITURE ============
        # Desks
        'desk': ['desk', 'desks', 'office desk', 'work desk'],
        'computer desk': ['computer desk', 'pc desk', 'gaming desk'],
        'corner desk': ['corner desk', 'l-shaped desk', 'l shaped desk', 'corner workstation'],
        'sit stand desk': ['sit stand desk', 'standing desk', 'height adjustable desk', 'electric desk', 'motorized desk'],
        'study desk': ['study desk', 'student desk', 'homework desk'],
        'reception desk': ['reception desk', 'reception counter', 'front desk'],
        'desk frame': ['desk frame', 'table frame', 'desk legs', 'table legs'],
        'drawing desk': ['drawing desk', 'drafting table', 'artist desk'],
        
        # Chairs
        'chair': ['chair', 'chairs', 'seating', 'seat'],
        'gaming chair': ['gaming chair', 'gamer chair', 'racing chair', 'rgb chair'],
        'executive chair': ['executive chair', 'boss chair', 'ceo chair', 'leather chair', 'high back chair'],
        'mesh chair': ['mesh chair', 'mesh office chair', 'breathable chair', 'mesh back chair'],
        'ergonomic chair': ['ergonomic chair', 'ergonomic office chair', 'posture chair', 'lumbar support chair'],
        'computer chair': ['computer chair', 'desk chair', 'office chair', 'swivel chair'],
        'massage chair': ['massage chair', 'massage office chair', 'heated chair'],
        'visitor chair': ['visitor chair', 'guest chair', 'waiting chair', 'reception chair'],
        
        # Tables
        'table': ['table', 'tables'],
        'boardroom table': ['boardroom table', 'conference table', 'meeting table', 'board table'],
        'coffee table': ['coffee table', 'cocktail table', 'center table'],
        'round table': ['round table', 'circular table'],
        'folding table': ['folding table', 'foldable table', 'portable table'],
        'bar table': ['bar table', 'pub table', 'high table', 'standing table'],
        
        # Filing & Storage
        'filing cabinet': ['filing cabinet', 'file cabinet', 'filing drawer', 'document cabinet'],
        'bookcase': ['bookcase', 'bookshelf', 'book shelf', 'bookshelves'],
        'pedestal': ['pedestal', 'pedestal drawer', 'mobile pedestal', 'desk pedestal'],
        'office shelving': ['office shelving', 'office shelf', 'storage shelf'],
        'storage cabinet': ['storage cabinet', 'cupboard', 'office cupboard'],
        'credenza': ['credenza', 'sideboard', 'sliding door cabinet'],
        
        # Office Accessories
        'monitor arm': ['monitor arm', 'monitor mount', 'screen arm', 'dual monitor arm', 'monitor stand'],
        'power point': ['power point', 'powerpoint', 'desk power', 'usb charger', 'power strip'],
        'desk screen': ['desk screen', 'privacy screen', 'partition', 'desk divider'],
        'vertical garden': ['vertical garden', 'wall planter', 'office plant', 'green wall'],
        'whiteboard': ['whiteboard', 'white board', 'dry erase board', 'marker board'],
        
        # ============ HOSPITALITY FURNITURE ============
        'bar stool': ['bar stool', 'bar stools', 'counter stool', 'high stool', 'pub stool'],
        'cafe chair': ['cafe chair', 'bistro chair', 'restaurant chair', 'dining chair'],
        'cafe table': ['cafe table', 'bistro table', 'restaurant table'],
        'sofa': ['sofa', 'sofas', 'couch', 'couches', 'settee', 'loveseat', 'lounge', 'sectional'],
        'reception seating': ['reception seating', 'waiting room chair', 'lobby seating', 'reception sofa'],
        'outdoor furniture': ['outdoor furniture', 'patio furniture', 'garden furniture', 'outdoor chair', 'outdoor table'],
        
        # ============ HOME FURNITURE ============
        'bedside table': ['bedside table', 'nightstand', 'night table', 'side table'],
        'shoe cabinet': ['shoe cabinet', 'shoe storage', 'shoe rack', 'entryway cabinet'],
        'mattress': ['mattress', 'mattresses', 'bed mattress', 'foam mattress', 'spring mattress'],
        'tv unit': ['tv unit', 'tv stand', 'entertainment unit', 'media unit', 'tv cabinet'],
        'ottoman': ['ottoman', 'ottomans', 'footstool', 'pouf', 'storage ottoman'],
        'bed': ['bed', 'beds', 'bed frame', 'bedframe', 'bedroom bed'],
        'bedroom furniture': ['bedroom furniture', 'bedroom set', 'wardrobe', 'dresser', 'chest of drawers'],
        'living room': ['living room', 'living room furniture', 'lounge furniture'],
        'dining room': ['dining room', 'dining table', 'dining chairs', 'dining set'],
        'kids furniture': ['kids furniture', 'children furniture', 'kids bed', 'kids desk', 'bunk bed'],
        'bathroom furniture': ['bathroom furniture', 'bathroom cabinet', 'vanity', 'bathroom shelf'],
        
        # ============ PET PRODUCTS ============
        # Dog Products
        'dog': ['dog', 'dogs', 'puppy', 'puppies', 'canine', 'pet dog'],
        'dog kennel': ['dog kennel', 'kennel', 'dog house', 'dog shelter', 'outdoor kennel'],
        'dog pram': ['dog pram', 'dog stroller', 'pet stroller', 'dog buggy'],
        'dog toy': ['dog toy', 'dog toys', 'chew toy', 'fetch toy', 'squeaky toy'],
        'dog cage': ['dog cage', 'dog crate', 'pet crate', 'wire crate', 'travel crate'],
        'dog training pad': ['dog training pad', 'puppy pad', 'pee pad', 'potty pad', 'wee pad'],
        'dog bowl': ['dog bowl', 'dog bowls', 'pet bowl', 'water bowl', 'food bowl', 'dog dispenser'],
        'dog car seat': ['dog car seat', 'pet car seat', 'car seat cover', 'dog hammock'],
        'dog collar': ['dog collar', 'dog collars', 'dog lead', 'dog leash', 'harness'],
        
        # Cat Products
        'cat': ['cat', 'cats', 'kitten', 'kittens', 'feline', 'kitty'],
        'cat tree': ['cat tree', 'cat tower', 'cat condo', 'cat scratching post', 'cat climbing tree'],
        'cat litter': ['cat litter', 'litter box', 'litter tray', 'cat toilet', 'self cleaning litter'],
        'cat bed': ['cat bed', 'cat bedding', 'cat cushion', 'cat hammock'],
        'cat carrier': ['cat carrier', 'cat cage', 'pet carrier', 'travel carrier'],
        'cat toy': ['cat toy', 'cat toys', 'cat teaser', 'cat wand', 'cat laser'],
        'cat bowl': ['cat bowl', 'cat bowls', 'cat feeder', 'cat food dispenser', 'cat fountain'],
        
        # Other Pet Products
        'bird cage': ['bird cage', 'bird cages', 'aviary', 'aviaries', 'bird stand', 'parrot cage'],
        'pet farm': ['pet farm', 'farm supplies', 'chicken feeder', 'poultry supplies'],
        'pet coop': ['pet coop', 'chicken coop', 'rabbit hutch', 'guinea pig cage', 'hutch'],
        
        # Aquarium
        'aquarium': ['aquarium', 'aquariums', 'fish tank', 'fish tanks', 'aquatic', 'fishbowl'],
        'aquarium pump': ['aquarium pump', 'fish tank pump', 'air pump', 'water pump', 'submersible pump'],
        'aquarium filter': ['aquarium filter', 'fish tank filter', 'canister filter', 'external filter', 'internal filter'],
    }
    
    # Category aliases - maps related categories together
    CATEGORY_ALIASES = {
        # Office Furniture aliases
        'desk': ['computer desk', 'corner desk', 'sit stand desk', 'study desk'],
        'chair': ['gaming chair', 'executive chair', 'mesh chair', 'ergonomic chair', 'computer chair'],
        'table': ['boardroom table', 'coffee table', 'bar table'],
        'storage': ['filing cabinet', 'bookcase', 'pedestal', 'credenza'],
        # Home Furniture aliases
        'sofa': ['lounge', 'settee', 'reception seating'],
        'bed': ['mattress', 'bedroom furniture'],
        # Sports & Fitness aliases
        'boxing': ['boxing gloves', 'boxing bag', 'focus pads', 'kick shields', 'muay thai'],
        'mma': ['mma gloves', 'mma shorts', 'rashguard', 'grappling'],
        'martial arts': ['martial arts uniform', 'training weapons', 'martial arts protective'],
        'gym': ['fitness', 'gym bench', 'strength equipment'],
        'fitness': ['treadmill', 'exercise bike', 'rowing', 'functional fitness'],
        'weightlifting': ['barbell', 'weight plates', 'dumbbell', 'kettlebell'],
        'functional fitness': ['strength equipment', 'conditioning', 'speed agility', 'body weight', 'mobility recovery'],
        # Pet aliases
        'dog': ['dog kennel', 'dog cage', 'dog bowl', 'dog collar', 'dog toy', 'dog pram'],
        'cat': ['cat tree', 'cat litter', 'cat carrier', 'cat toy', 'cat bowl'],
        'aquarium': ['aquarium pump', 'aquarium filter'],
        'pet': ['dog', 'cat', 'bird cage', 'pet coop'],
        # Electric Scooters aliases
        'scooter': ['scooter accessories'],
    }
    
    # Incompatible keyword pairs - if query has key, penalize results with values
    NEGATIVE_KEYWORDS = {
        # Office/Gaming exclusions
        'gaming': ['kids', 'kid', 'children', 'child', 'baby', 'toddler', 'toy', 'playground', 'plastic'],
        'office': ['kids', 'kid', 'children', 'child', 'baby', 'toddler', 'toy', 'playground'],
        'professional': ['kids', 'kid', 'children', 'child', 'baby', 'toy', 'plastic'],
        'executive': ['kids', 'kid', 'children', 'child', 'baby', 'toy', 'plastic'],
        'ergonomic': ['kids', 'kid', 'children', 'toy', 'plastic'],
        'adult': ['kids', 'kid', 'children', 'child', 'baby', 'toddler', 'toy'],
        'premium': ['cheap', 'budget', 'plastic', 'toy'],
        'luxury': ['cheap', 'budget', 'plastic', 'toy'],
        'leather': ['plastic', 'pvc'],
        'metal': ['plastic', 'cardboard'],
        'wood': ['plastic', 'cardboard'],
        'kids': ['office', 'executive', 'professional', 'gaming', 'adult'],
        'children': ['office', 'executive', 'professional', 'gaming', 'adult'],
        # Pet-specific negatives (don't mix pet types or with furniture)
        'aquarium': ['furniture', 'chair', 'desk', 'bed', 'sofa', 'dog', 'cat'],
        'dog': ['cat', 'bird', 'fish', 'rabbit', 'aquarium'],
        'cat': ['dog', 'bird', 'fish', 'rabbit', 'aquarium'],
        'bird': ['dog', 'cat', 'fish', 'aquarium'],
        # Sports-specific negatives
        'boxing': ['yoga', 'meditation', 'pilates'],
        'mma': ['yoga', 'meditation', 'pilates'],
        'yoga': ['boxing', 'mma', 'weightlifting'],
    }
    
    # Intent-related keywords for boosting
    INTENT_KEYWORDS = {
        # Office Furniture intents
        'gaming': ['rgb', 'racing', 'ergonomic', 'reclining', 'adjustable', 'swivel', 'lumbar', 'gamer'],
        'office': ['ergonomic', 'executive', 'professional', 'swivel', 'adjustable', 'mesh', 'lumbar', 'commercial'],
        'home office': ['desk', 'chair', 'monitor', 'keyboard', 'ergonomic'],
        'reception': ['waiting', 'lobby', 'guest', 'visitor', 'front desk'],
        # Home Furniture intents
        'kids': ['child', 'children', 'youth', 'junior', 'study', 'colorful', 'small', 'bunk'],
        'bedroom': ['bed', 'nightstand', 'dresser', 'wardrobe', 'sleeping', 'mattress'],
        'living room': ['sofa', 'couch', 'lounge', 'recliner', 'armchair', 'ottoman', 'coffee table', 'tv unit'],
        'dining': ['dining table', 'dining chairs', 'buffet', 'sideboard'],
        'outdoor': ['weather', 'waterproof', 'patio', 'garden', 'resistant', 'uv'],
        # Sports & Fitness intents
        'boxing': ['gloves', 'bag', 'wraps', 'pads', 'ring', 'sparring', 'heavy bag', 'muay thai'],
        'mma': ['gloves', 'shorts', 'rashguard', 'grappling', 'sparring', 'cage', 'ufc'],
        'martial arts': ['gi', 'uniform', 'belt', 'training', 'dojo', 'karate', 'taekwondo', 'judo'],
        'fitness': ['workout', 'exercise', 'training', 'strength', 'cardio', 'gym', 'hiit'],
        'gym': ['weights', 'bench', 'rack', 'barbell', 'dumbbell', 'machine', 'cable'],
        'cardio': ['treadmill', 'bike', 'rowing', 'elliptical', 'running', 'cycling'],
        'weightlifting': ['barbell', 'plates', 'rack', 'bench', 'olympic', 'powerlifting'],
        'functional': ['crossfit', 'hiit', 'circuit', 'kettlebell', 'battle ropes', 'plyo'],
        'training': ['workout', 'exercise', 'fitness', 'equipment', 'gear', 'professional'],
        # Pet intents
        'aquarium': ['fish', 'tank', 'filter', 'pump', 'water', 'aquatic', 'marine', 'tropical'],
        'dog': ['kennel', 'crate', 'bed', 'collar', 'leash', 'toy', 'food', 'puppy', 'training'],
        'cat': ['tree', 'scratching', 'litter', 'bed', 'toy', 'food', 'kitten', 'climbing'],
        'pet': ['supplies', 'food', 'bed', 'carrier', 'bowl', 'feeder', 'grooming'],
        'bird': ['cage', 'aviary', 'perch', 'feeder', 'parrot', 'budgie'],
        # Electric Scooter intents
        'scooter': ['electric', 'commute', 'folding', 'portable', 'wheel', 'battery'],
    }
    
    # Query expansion - map common synonyms to search terms
    QUERY_SYNONYMS = {
        # Price synonyms
        'cheap': ['budget', 'affordable', 'value', 'low price'],
        'expensive': ['premium', 'luxury', 'high-end', 'designer'],
        # Furniture synonyms
        'couch': ['sofa', 'settee', 'lounge'],
        'cupboard': ['cabinet', 'storage', 'wardrobe'],
        'wardrobe': ['closet', 'armoire', 'clothes storage'],
        'nightstand': ['bedside table', 'night table', 'end table'],
        'dresser': ['chest of drawers', 'bureau', 'drawers'],
        'bookshelf': ['bookcase', 'shelving', 'book storage'],
        'lamp': ['light', 'lighting', 'table lamp'],
        'rug': ['carpet', 'floor mat', 'area rug'],
        # Size synonyms
        'small': ['compact', 'mini', 'little'],
        'big': ['large', 'oversized', 'spacious'],
        # Style synonyms
        'modern': ['contemporary', 'minimalist', 'sleek'],
        'rustic': ['farmhouse', 'country', 'vintage'],
        'comfy': ['comfortable', 'cozy', 'plush'],
        # Sports & Fitness synonyms
        'punching bag': ['heavy bag', 'boxing bag', 'kick bag'],
        'boxing gloves': ['sparring gloves', 'training gloves', 'bag gloves'],
        'weights': ['dumbbells', 'barbells', 'kettlebells'],
        'treadmill': ['running machine', 'walking machine'],
        'exercise bike': ['spin bike', 'stationary bike', 'cycling bike'],
        'rowing machine': ['rower', 'erg', 'ergometer'],
        'focus mitts': ['focus pads', 'punch mitts', 'target pads'],
        'thai pads': ['kick pads', 'kick shields'],
        # Pet synonyms
        'fish tank': ['aquarium', 'fish bowl'],
        'dog crate': ['kennel', 'dog house', 'dog cage'],
        'cat tower': ['cat tree', 'scratching post', 'cat condo'],
        'puppy pad': ['training pad', 'pee pad', 'potty pad'],
        'pet carrier': ['travel carrier', 'cat carrier', 'dog carrier'],
        # Electric scooter synonyms
        'e-scooter': ['electric scooter', 'escooter'],
    }
    
    def __init__(self, bm25_index: BM25Index, vector_index: VectorIndex, alpha: float = 0.5):
        self.bm25_index = bm25_index
        self.vector_index = vector_index
        self.alpha = alpha
        self._query_cache = {}  # Cache for query expansion
        self._cache_max_size = 200
    
    def _expand_query(self, query: str) -> str:
        """
        Expand query with synonyms for better recall.
        
        Args:
            query: Original search query
            
        Returns:
            Expanded query with synonyms added
        """
        # Check cache first
        if query in self._query_cache:
            return self._query_cache[query]
        
        query_lower = query.lower()
        expanded_terms = [query_lower]
        
        # Add synonyms for any matching words
        for word, synonyms in self.QUERY_SYNONYMS.items():
            if word in query_lower:
                # Add first 2 synonyms to avoid query explosion
                expanded_terms.extend(synonyms[:2])
        
        # Build expanded query (original + key synonyms)
        expanded = ' '.join(expanded_terms)
        
        # Cache the result
        if len(self._query_cache) >= self._cache_max_size:
            # Clear oldest entry
            first_key = next(iter(self._query_cache))
            del self._query_cache[first_key]
        self._query_cache[query] = expanded
        
        if expanded != query_lower:
            print(f"[HYBRID_SEARCH] Query expanded: '{query}' -> '{expanded[:80]}...'")
        
        return expanded
    
    def _extract_primary_category(self, query: str) -> Tuple[Optional[str], List[str]]:
        """
        Extract the primary product category and related categories from query.
        
        Returns:
            Tuple of (primary_category, list of all matching keywords)
        """
        query_lower = query.lower()
        
        # Check for category keywords in order of specificity (most specific first)
        priority_order = [
            # ===== PET PRODUCTS (most specific first) =====
            'aquarium pump', 'aquarium filter', 'aquarium',  # Aquarium specific
            'dog kennel', 'dog cage', 'dog pram', 'dog toy', 'dog bowl', 'dog collar', 'dog car seat', 'dog training pad',
            'cat tree', 'cat litter', 'cat carrier', 'cat toy', 'cat bowl', 'cat bed',
            'bird cage', 'pet coop', 'pet farm',
            'dog', 'cat', 'pet',  # General pet categories
            
            # ===== SPORTS & FITNESS (most specific first) =====
            # Boxing & MMA
            'boxing gloves', 'mma gloves', 'boxing bag', 'focus pads', 'kick shields', 
            'boxing ring', 'boxing apparel', 'protective equipment',
            'mma shorts', 'rashguard',
            'boxing', 'mma',
            # Martial Arts
            'martial arts uniform', 'training weapons', 'martial arts protective', 'martial arts',
            # Gym Equipment
            'gym bench', 'air track', 'trampoline',
            'treadmill', 'exercise bike', 'rowing',
            'dumbbell', 'kettlebell', 'barbell', 'weight plates',
            # Functional Fitness
            'strength equipment', 'conditioning', 'speed agility', 'body weight', 'mobility recovery',
            'functional fitness', 'weightlifting',
            # General Fitness
            'fitness', 'gym',
            # Sports
            'rugby', 'basketball',
            
            # ===== ELECTRIC SCOOTERS =====
            'scooter accessories', 'scooter',
            
            # ===== OFFICE FURNITURE (most specific first) =====
            # Desks
            'computer desk', 'corner desk', 'sit stand desk', 'study desk', 'reception desk', 
            'desk frame', 'drawing desk', 'desk',
            # Chairs  
            'gaming chair', 'executive chair', 'mesh chair', 'ergonomic chair', 'computer chair',
            'massage chair', 'visitor chair', 'chair',
            # Tables
            'boardroom table', 'coffee table', 'round table', 'folding table', 'bar table', 'table',
            # Storage
            'filing cabinet', 'bookcase', 'pedestal', 'office shelving', 'storage cabinet', 'credenza', 'storage',
            # Accessories
            'monitor arm', 'power point', 'desk screen', 'vertical garden', 'whiteboard',
            
            # ===== HOSPITALITY FURNITURE =====
            'bar stool', 'cafe chair', 'cafe table', 'reception seating', 'outdoor furniture',
            'sofa',
            
            # ===== HOME FURNITURE =====
            'bedside table', 'shoe cabinet', 'mattress', 'tv unit', 'ottoman',
            'bedroom furniture', 'living room', 'dining room', 'kids furniture', 'bathroom furniture',
            'bed',
        ]
        
        for category in priority_order:
            if category in self.CATEGORY_KEYWORDS:
                keywords = self.CATEGORY_KEYWORDS[category]
                for keyword in keywords:
                    if keyword in query_lower:
                        # Get all related keywords including aliases
                        all_keywords = list(keywords)
                        if category in self.CATEGORY_ALIASES:
                            for alias in self.CATEGORY_ALIASES[category]:
                                if alias in self.CATEGORY_KEYWORDS:
                                    all_keywords.extend(self.CATEGORY_KEYWORDS[alias])
                        
                        print(f"[HYBRID_SEARCH] Extracted category: {category} (matched '{keyword}' in query '{query}')")
                        print(f"[HYBRID_SEARCH] All matching keywords: {all_keywords[:10]}...")
                        return category, list(set(all_keywords))
        
        print(f"[HYBRID_SEARCH] No category extracted from query: {query}")
        return None, []
    
    def _check_category_match(self, text: str, category_keywords: List[str], primary_category: str = None) -> Tuple[bool, float]:
        """
        Check if text matches any category keywords.
        
        Returns:
            Tuple of (has_match, match_score)
            - has_match: True if any keyword found
            - match_score: 0.0-1.0 indicating strength of match
        """
        text_lower = text.lower()
        matches = 0
        primary_match = False
        
        for keyword in category_keywords:
            if keyword in text_lower:
                matches += 1
                # Exact word match is stronger
                if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                    matches += 1
                    # If the primary category word itself matches (e.g., "sofa" in "reception sofa")
                    if primary_category and keyword == primary_category:
                        primary_match = True
                        matches += 3  # Strong boost for exact primary category match
        
        if matches > 0:
            # Normalize score (cap at 1.0)
            base_score = min(matches / 4.0, 1.0)
            # Extra boost if primary category matches
            if primary_match:
                base_score = min(base_score * 1.5, 1.0)
            return True, base_score
        
        return False, 0.0
    
    def _extract_intent_keywords(self, query: str) -> List[str]:
        """Extract intent keywords from query (gaming, office, kids, etc.)."""
        query_lower = query.lower()
        found_intents = []
        
        for intent in self.INTENT_KEYWORDS.keys():
            if intent in query_lower:
                found_intents.append(intent)
        
        return found_intents
    
    def _calculate_negative_keyword_penalty(self, query: str, title: str, description: str) -> float:
        """Calculate penalty for incompatible keywords.
        
        Returns a multiplier: 1.0 (no penalty) to 0.1 (heavy penalty)
        """
        query_lower = query.lower()
        text_lower = (title + ' ' + description).lower()
        
        penalty = 1.0
        
        for query_keyword, negative_keywords in self.NEGATIVE_KEYWORDS.items():
            if query_keyword in query_lower:
                for negative_keyword in negative_keywords:
                    if negative_keyword in text_lower:
                        # Heavy penalty for incompatible context
                        penalty *= 0.1
                        break  # One penalty per query keyword is enough
        
        return penalty
    
    def _calculate_intent_boost(self, query: str, title: str, description: str) -> float:
        """Boost results that match query intent.
        
        Returns a multiplier: 1.0 (no boost) to 2.0 (strong boost)
        """
        intent_keywords = self._extract_intent_keywords(query)
        
        if not intent_keywords:
            return 1.0  # No intent detected
        
        text_lower = (title + ' ' + description).lower()
        boost = 1.0
        
        for intent in intent_keywords:
            related_keywords = self.INTENT_KEYWORDS.get(intent, [])
            matched_count = sum(1 for kw in related_keywords if kw in text_lower)
            
            if matched_count > 0:
                # Boost based on how many related keywords matched
                boost += 0.3 * min(matched_count, 3)  # Cap at 3 keywords
        
        return min(boost, 2.0)  # Cap at 2.0x
    
    def _calculate_phrase_score(self, query: str, title: str, description: str) -> float:
        """
        Calculate phrase matching score.
        
        Boosts results where:
        - Exact phrase appears in title (highest boost - 10x)
        - All query terms appear in title (high boost - 5x)
        - Exact phrase appears in description (medium boost - 3x)
        - All query terms appear in description (low boost - 2x)
        """
        query_lower = query.lower().strip()
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Exact phrase in title = 10x boost (increased from 5x)
        if query_lower in title_lower:
            return 10.0
        
        # All words in title = 5x boost (increased from 3x)
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        title_words = set(re.findall(r'\b\w+\b', title_lower))
        if query_words.issubset(title_words):
            return 5.0
        
        # Exact phrase in description = 3x boost (increased from 2x)
        if query_lower in desc_lower:
            return 3.0
        
        # All words in description = 2x boost (increased from 1.5x)
        desc_words = set(re.findall(r'\b\w+\b', desc_lower))
        if query_words.issubset(desc_words):
            return 2.0
        
        # Partial match in title (at least 50% of query words)
        title_match_count = len(query_words & title_words)
        if title_match_count > 0:
            match_ratio = title_match_count / len(query_words)
            if match_ratio >= 0.5:
                return 1.0 + (match_ratio * 0.5)  # 1.0 to 1.5x boost
        
        return 1.0  # No boost
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid search using Reciprocal Rank Fusion with enhanced phrase matching.
        Optimized for large catalogs (2000+ products).
        
        Improvements:
        - Query expansion with synonyms for better recall
        - Phrase matching score boost (10x for exact match)
        - Semantic similarity threshold filtering
        - Category-based filtering with smart fallback
        - Negative keyword penalties
        - Intent-based boosting
        - Better handling of multi-word queries
        - Important noun requirement for furniture queries
        """
        query_lower = query.lower()
        
        # Expand query with synonyms for better recall
        expanded_query = self._expand_query(query_lower)
        
        # Extract primary category and all related keywords
        primary_category, category_keywords = self._extract_primary_category(query_lower)
        
        # Get more results for filtering (increased for large catalogs)
        candidate_limit = min(limit * 10, 100)  # Get 10x but cap at 100
        
        # Use expanded query for BM25 (keyword-based), original for vector (semantic)
        bm25_results = self.bm25_index.search(expanded_query, limit=candidate_limit)
        vector_results = self.vector_index.search(query_lower, limit=candidate_limit)
        
        print(f"[HYBRID_SEARCH] BM25 returned {len(bm25_results)} results, Vector returned {len(vector_results)} results")
        
        # Semantic similarity threshold (ChromaDB uses distance, lower is better)
        # For cosine distance: 0 = identical, 2 = opposite
        # Relaxed threshold for large catalogs with diverse products
        SEMANTIC_THRESHOLD = 0.85
        
        combined_scores = {}
        query_terms = set(query_lower.split())
        
        # Pre-extract important query nouns
        important_query_terms = query_terms & self.IMPORTANT_NOUNS
        unique_base_nouns = set()
        for noun in important_query_terms:
            if noun.endswith('s') and noun[:-1] in self.IMPORTANT_NOUNS:
                unique_base_nouns.add(noun[:-1])
            else:
                unique_base_nouns.add(noun)
        
        # BM25 scores with category and negative keyword filtering
        for rank, result in enumerate(bm25_results, start=1):
            doc_id = result['id']
            rrf_score = 1.0 / (60 + rank)
            
            content = result.get('content', {})
            title = content.get('title', '').lower()
            description = content.get('description', '').lower()
            
            # Calculate phrase matching boost
            phrase_boost = self._calculate_phrase_score(query, title, description)
            
            # Calculate negative keyword penalty
            negative_penalty = self._calculate_negative_keyword_penalty(query, title, description)
            
            # Calculate intent boost
            intent_boost = self._calculate_intent_boost(query, title, description)
            
            # Legacy title boost (kept for compatibility)
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            legacy_title_boost = 1.0 + (title_match_count * 0.5)
            
            # Use maximum of phrase boost and legacy boost, apply penalties and boosts
            final_boost = max(phrase_boost, legacy_title_boost) * intent_boost * negative_penalty
            
            combined_scores[doc_id] = {
                'score': self.alpha * rrf_score * final_boost,
                'result': result,
                'bm25_rank': rank,
                'vector_rank': None,
                'semantic_distance': None,
                'phrase_boost': phrase_boost,
                'title_boost': final_boost,
                'negative_penalty': negative_penalty,
                'intent_boost': intent_boost
            }
        
        # Vector scores with semantic threshold filtering
        for rank, result in enumerate(vector_results, start=1):
            doc_id = result['id']
            semantic_distance = result.get('score', 0.0)
            
            # Filter out results with low semantic similarity
            if semantic_distance > SEMANTIC_THRESHOLD:
                continue  # Skip semantically distant results
            
            rrf_score = 1.0 / (60 + rank)
            
            content = result.get('content', {})
            title = content.get('title', '').lower()
            description = content.get('description', '').lower()
            
            # Calculate phrase matching boost
            phrase_boost = self._calculate_phrase_score(query, title, description)
            
            # Calculate negative keyword penalty
            negative_penalty = self._calculate_negative_keyword_penalty(query, title, description)
            
            # Calculate intent boost
            intent_boost = self._calculate_intent_boost(query, title, description)
            
            # Legacy title boost
            title_words = set(title.split())
            title_match_count = len(query_terms & title_words)
            legacy_title_boost = 1.0 + (title_match_count * 0.5)
            
            final_boost = max(phrase_boost, legacy_title_boost) * intent_boost * negative_penalty
            
            if doc_id in combined_scores:
                combined_scores[doc_id]['score'] += (1 - self.alpha) * rrf_score * final_boost
                combined_scores[doc_id]['vector_rank'] = rank
                combined_scores[doc_id]['semantic_distance'] = semantic_distance
                combined_scores[doc_id]['phrase_boost'] = max(
                    combined_scores[doc_id].get('phrase_boost', 1.0),
                    phrase_boost
                )
                combined_scores[doc_id]['title_boost'] = max(
                    combined_scores[doc_id]['title_boost'],
                    final_boost
                )
                combined_scores[doc_id]['negative_penalty'] = min(
                    combined_scores[doc_id].get('negative_penalty', 1.0),
                    negative_penalty
                )
                combined_scores[doc_id]['intent_boost'] = max(
                    combined_scores[doc_id].get('intent_boost', 1.0),
                    intent_boost
                )
            else:
                combined_scores[doc_id] = {
                    'score': (1 - self.alpha) * rrf_score * final_boost,
                    'result': result,
                    'bm25_rank': None,
                    'vector_rank': rank,
                    'semantic_distance': semantic_distance,
                    'phrase_boost': phrase_boost,
                    'title_boost': final_boost,
                    'negative_penalty': negative_penalty,
                    'intent_boost': intent_boost
                }
        
        # Sort and apply filters/boosts with smart category matching
        sorted_candidates = sorted(combined_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # FIRST PASS: Strict category filtering
        category_matched = []
        category_unmatched = []
        
        print(f"[HYBRID_SEARCH] Primary category: {primary_category}")
        print(f"[HYBRID_SEARCH] Category keywords: {category_keywords[:5]}..." if category_keywords else "[HYBRID_SEARCH] No category keywords")
        print(f"[HYBRID_SEARCH] Processing {len(sorted_candidates)} candidates")
        
        filtered_count = 0
        for doc_id, data in sorted_candidates:
            title = data['result'].get('content', {}).get('title', '').lower()
            description = data['result'].get('content', {}).get('description', '').lower()
            tags = str(data['result'].get('content', {}).get('tags', '')).lower()
            product_type = str(data['result'].get('content', {}).get('type', '')).lower()
            
            # Combine all text fields for matching
            text = f"{title} {description} {tags} {product_type}"
            
            # Check category match using expanded keywords
            if primary_category and category_keywords:
                # Pass primary_category for stronger matching
                has_match, match_score = self._check_category_match(text, category_keywords, primary_category)
                
                # STRICT CHECK: Does the title contain the primary category word?
                title_has_primary = primary_category in title
                
                if has_match:
                    # Extra boost if primary category is directly in the title
                    if title_has_primary:
                        data['score'] *= (1.5 + match_score)  # Stronger boost
                        data['primary_title_match'] = True
                    else:
                        data['score'] *= (1.0 + match_score * 0.5)  # Weaker boost for non-title matches
                        data['primary_title_match'] = False
                    data['category_match'] = True
                    category_matched.append((doc_id, data))
                else:
                    filtered_count += 1
                    if filtered_count <= 3:
                        print(f"[HYBRID_SEARCH] ❌ FILTERED: '{title[:50]}' (no match for category '{primary_category}')")
                    data['category_match'] = False
                    category_unmatched.append((doc_id, data))
            else:
                # No category filter - include all
                data['category_match'] = True
                category_matched.append((doc_id, data))
        
        # Sort category_matched by score (so title matches come first)
        category_matched.sort(key=lambda x: x[1]['score'], reverse=True)
        
        # FALLBACK: If strict filtering yields too few results, include some unmatched
        MIN_RESULTS = 3
        if len(category_matched) < MIN_RESULTS and category_unmatched:
            print(f"[HYBRID_SEARCH] ⚠️ Only {len(category_matched)} category matches, adding fallback results")
            
            # Sort unmatched by score and add top ones with penalty
            category_unmatched.sort(key=lambda x: x[1]['score'], reverse=True)
            for doc_id, data in category_unmatched[:MIN_RESULTS - len(category_matched)]:
                data['score'] *= 0.3  # Heavier penalty for non-matching category
                data['is_fallback'] = True
                category_matched.append((doc_id, data))
                title = data['result'].get('content', {}).get('title', '')
                print(f"[HYBRID_SEARCH] ➕ FALLBACK: '{title[:50]}'")
        
        # Apply noun matching and build final results
        final_results = []
        
        for doc_id, data in category_matched:
            title = data['result'].get('content', {}).get('title', '').lower()
            
            # Apply noun matching filter (only for furniture queries with nouns)
            if unique_base_nouns:
                matched_count = 0
                for base in unique_base_nouns:
                    if base in title or (base + 's') in title:
                        matched_count += 1
                
                match_ratio = matched_count / len(unique_base_nouns) if unique_base_nouns else 0
                
                # Boost products with all nouns matched
                if match_ratio >= 1.0:
                    data['score'] *= 2.0  # Full match - strong boost
                elif match_ratio >= 0.5:
                    data['score'] *= 1.5  # Partial match - medium boost
                elif match_ratio > 0:
                    data['score'] *= 1.2  # At least one noun - small boost
                # Don't penalize if category already matched
            
            final_results.append({
                'id': doc_id,
                'score': data['score'],
                'content': data['result']['content'],
                'bm25_rank': data['bm25_rank'],
                'vector_rank': data['vector_rank'],
                'semantic_distance': data.get('semantic_distance'),
                'phrase_boost': data.get('phrase_boost', 1.0),
                'negative_penalty': data.get('negative_penalty', 1.0),
                'intent_boost': data.get('intent_boost', 1.0),
                'category_match': data.get('category_match', False),
                'is_fallback': data.get('is_fallback', False)
            })
            
            if len(final_results) >= limit + 5:  # Get a few extra for final re-sort
                break
        
        # Final re-sort after all boosts applied
        final_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Log final results
        print(f"[HYBRID_SEARCH] ✅ Returning {min(len(final_results), limit)} results")
        if final_results:
            for i, r in enumerate(final_results[:3]):
                title = r['content'].get('title', 'Unknown')[:40]
                print(f"[HYBRID_SEARCH]   {i+1}. {title}... (score: {r['score']:.4f}, cat_match: {r.get('category_match', '?')})")
        
        return final_results[:limit]
