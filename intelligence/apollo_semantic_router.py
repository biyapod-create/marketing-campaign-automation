"""
Apollo Semantic Router
Translates natural language queries into exact Apollo.io API parameters.

Example:
    "find 30 SMEs in Abuja that need Allennetic services"
    → organization_search with specific filters
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class QueryIntent(Enum):
    """Classification of user intent"""
    FIND_COMPANIES = "find_companies"
    FIND_PEOPLE = "find_people"
    ENRICH_COMPANY = "enrich_company"
    ENRICH_PERSON = "enrich_person"
    FIND_EMPLOYEES = "find_employees"


@dataclass
class ParsedQuery:
    """Structured representation of user's natural language query"""
    intent: QueryIntent
    location: Optional[str] = None
    company_size: Optional[str] = None
    job_titles: Optional[List[str]] = None
    seniorities: Optional[List[str]] = None
    industry: Optional[str] = None
    count: int = 25
    raw_query: str = ""


class ApolloSemanticRouter:
    """
    Intelligent router that maps natural language to Apollo API calls.
    
    This is the intelligence layer that prevents guessing and ensures
    every query maps to the correct Apollo endpoint with exact parameters.
    """
    
    # Allennetic's ideal customer profile patterns
    ALLENNETIC_ICP = {
        'keywords': [
            'startups', 'small business', 'sme', 'solopreneur', 
            'freelancer', 'new business', 'e-commerce', 'digital',
            'restaurant', 'salon', 'clinic', 'ngo', 'consultant',
            'coach', 'photographer', 'retail'
        ],
        'signals': {
            'needs_website': ['no website', 'needs website', 'digital presence'],
            'needs_email': ['gmail', 'yahoo', 'needs professional email'],
            'new_business': ['just incorporated', 'new', 'starting'],
            'going_digital': ['going digital', 'online', 'digital transformation']
        },
        'locations': {
            'abuja': 'Abuja, Federal Capital Territory, Nigeria',
            'lagos': 'Lagos, Lagos, Nigeria',
            'port harcourt': 'Port Harcourt, Rivers, Nigeria',
            'nigeria': 'Nigeria'
        },
        'company_sizes': {
            'startup': ['1-10'],
            'sme': ['1-10', '11-50'],
            'small': ['1-10', '11-50'],
            'micro': ['1-10'],
            'medium': ['51-200']
        }
    }
    
    # Title patterns for decision makers
    DECISION_MAKER_TITLES = [
        "CEO", "Founder", "Co-Founder", "Managing Director", 
        "Owner", "President", "Managing Partner", "Director"
    ]
    
    SENIORITY_MAPPING = {
        'founder': 'founder',
        'ceo': 'c_suite',
        'owner': 'owner',
        'director': 'director',
        'manager': 'manager',
        'vp': 'vp',
        'senior': 'senior'
    }
    
    def __init__(self):
        self.query_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for query parsing"""
        return {
            'count': re.compile(r'(\d+)\s*(?:leads|companies|people|contacts|smes?|businesses?)', re.IGNORECASE),
            'location': re.compile(r'(?:in|from|located in|at)\s+([A-Za-z\s]+?)(?=\s+(?:that|who|with)|$)', re.IGNORECASE),
            'needs_service': re.compile(r'(?:need|needs|require|want)\s+(website|email|digital|branding|payment)', re.IGNORECASE),
            'company_type': re.compile(r'\b(startup|sme|small business|micro|solopreneur|freelancer|e-commerce|restaurant|salon|clinic|ngo)\b', re.IGNORECASE),
            'job_title': re.compile(r'\b(ceo|founder|owner|director|manager|president)\b', re.IGNORECASE),
        }
    
    def parse(self, natural_query: str) -> ParsedQuery:
        """
        Main parsing function. Translates natural language to structured query.
        
        Args:
            natural_query: User's natural language input
            
        Returns:
            ParsedQuery object with structured parameters
        """
        query_lower = natural_query.lower()
        
        # Determine intent
        intent = self._detect_intent(query_lower)
        
        # Extract parameters
        count = self._extract_count(natural_query)
        location = self._extract_location(natural_query)
        company_size = self._extract_company_size(query_lower)
        job_titles = self._extract_job_titles(query_lower)
        seniorities = self._extract_seniorities(query_lower)
        
        return ParsedQuery(
            intent=intent,
            location=location,
            company_size=company_size,
            job_titles=job_titles,
            seniorities=seniorities,
            count=count,
            raw_query=natural_query
        )
    
    def _detect_intent(self, query: str) -> QueryIntent:
        """Determine what the user wants to do"""
        if any(word in query for word in ['find companies', 'find businesses', 'find sme', 'companies in']):
            return QueryIntent.FIND_COMPANIES
        elif any(word in query for word in ['find people', 'find founders', 'find ceos']):
            return QueryIntent.FIND_PEOPLE
        elif 'employees of' in query or 'people at' in query:
            return QueryIntent.FIND_EMPLOYEES
        else:
            # Default: if looking for Allennetic services, find companies
            if any(keyword in query for keyword in self.ALLENNETIC_ICP['keywords']):
                return QueryIntent.FIND_COMPANIES
            return QueryIntent.FIND_COMPANIES
    
    def _extract_count(self, query: str) -> int:
        """Extract number of results requested"""
        match = self.query_patterns['count'].search(query)
        return int(match.group(1)) if match else 25
    
    def _extract_location(self, query: str) -> Optional[str]:
        """Extract and normalize location"""
        match = self.query_patterns['location'].search(query)
        if match:
            location_raw = match.group(1).strip().lower()
            # Normalize to Apollo format
            for key, value in self.ALLENNETIC_ICP['locations'].items():
                if key in location_raw:
                    return value
            return location_raw.title()
        return None
    
    def _extract_company_size(self, query: str) -> Optional[str]:
        """Extract company size filter"""
        for size_type, size_range in self.ALLENNETIC_ICP['company_sizes'].items():
            if size_type in query:
                return ','.join(size_range)
        return None
    
    def _extract_job_titles(self, query: str) -> Optional[List[str]]:
        """Extract job titles to search for"""
        # Check if specific titles mentioned
        matches = self.query_patterns['job_title'].findall(query)
        if matches:
            titles = []
            for match in matches:
                if match.lower() in ['ceo', 'founder', 'owner']:
                    titles.extend(self.DECISION_MAKER_TITLES[:4])
                elif match.lower() == 'director':
                    titles.append('Managing Director')
            return list(set(titles)) if titles else None
        
        # Default for Allennetic: decision makers
        if 'allennetic' in query or 'need' in query:
            return self.DECISION_MAKER_TITLES[:5]
        
        return None
    
    def _extract_seniorities(self, query: str) -> Optional[List[str]]:
        """Extract seniority levels"""
        seniorities = []
        for keyword, apollo_value in self.SENIORITY_MAPPING.items():
            if keyword in query:
                seniorities.append(apollo_value)
        
        # Default for Allennetic: founders and owners
        if not seniorities and ('allennetic' in query or 'need' in query):
            return ['founder', 'c_suite', 'owner']
        
        return seniorities if seniorities else None
    
    def to_apollo_params(self, parsed: ParsedQuery) -> Dict:
        """
        Convert ParsedQuery to exact Apollo API parameters.
        
        This is the critical translation layer that ensures
        no guessing happens at the API level.
        """
        params = {}
        
        if parsed.intent == QueryIntent.FIND_COMPANIES:
            # Organization search parameters
            if parsed.location:
                params['organization_locations'] = [parsed.location]
            
            if parsed.company_size:
                params['organization_num_employees_ranges'] = parsed.company_size.split(',')
            
            # Add Allennetic-specific filters
            params['page'] = 1
            params['per_page'] = min(parsed.count, 100)
            
        elif parsed.intent == QueryIntent.FIND_PEOPLE:
            # People search parameters
            if parsed.job_titles:
                params['person_titles'] = parsed.job_titles
            
            if parsed.seniorities:
                params['person_seniorities'] = parsed.seniorities
            
            if parsed.location:
                params['person_locations'] = [parsed.location]
            
            params['page'] = 1
            params['per_page'] = min(parsed.count, 100)
        
        return params
    
    def route(self, natural_query: str) -> Tuple[str, Dict]:
        """
        Main routing function. Returns (tool_name, parameters)
        
        Args:
            natural_query: User's natural language input
            
        Returns:
            Tuple of (apollo_tool_name, exact_parameters)
            
        Example:
            >>> router = ApolloSemanticRouter()
            >>> tool, params = router.route("find 30 SMEs in Abuja that need websites")
            >>> print(tool)
            'organization_search'
            >>> print(params)
            {'organization_locations': ['Abuja, Federal Capital Territory, Nigeria'], 
             'organization_num_employees_ranges': ['1-10', '11-50'],
             'page': 1, 'per_page': 30}
        """
        parsed = self.parse(natural_query)
        params = self.to_apollo_params(parsed)
        
        # Map intent to Apollo tool
        tool_mapping = {
            QueryIntent.FIND_COMPANIES: 'organization_search',
            QueryIntent.FIND_PEOPLE: 'people_search',
            QueryIntent.ENRICH_COMPANY: 'organization_enrichment',
            QueryIntent.ENRICH_PERSON: 'people_enrichment',
            QueryIntent.FIND_EMPLOYEES: 'employees_of_company'
        }
        
        tool_name = tool_mapping[parsed.intent]
        
        return tool_name, params
    
    def explain_routing(self, natural_query: str) -> str:
        """
        Debug function: Explains how the query was interpreted.
        Useful for validation and transparency.
        """
        parsed = self.parse(natural_query)
        tool_name, params = self.route(natural_query)
        
        explanation = f"""
Query: "{natural_query}"

Interpretation:
- Intent: {parsed.intent.value}
- Location: {parsed.location or 'Not specified'}
- Count: {parsed.count}
- Job titles: {', '.join(parsed.job_titles) if parsed.job_titles else 'Not specified'}
- Seniorities: {', '.join(parsed.seniorities) if parsed.seniorities else 'Not specified'}
- Company size: {parsed.company_size or 'Not specified'}

Apollo Tool: {tool_name}
Parameters: {params}
"""
        return explanation.strip()
