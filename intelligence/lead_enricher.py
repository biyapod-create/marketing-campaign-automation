"""
Lead Enrichment Pipeline
========================
Connects Apollo.io MCP to enrich leads with actionable intelligence.

Responsibilities:
- Fetch company and person data
- Classify confidence levels
- Store enriched data
- Handle API failures gracefully
"""

import json
from typing import List, Dict, Optional
from dataclasses import asdict
from .decision_router import LeadIntelligence


class LeadEnricher:
    """
    Lead enrichment via Apollo.io MCP
    
    Confidence rules:
    - high: Full enrichment (industry, size, tech stack)
    - medium: Partial enrichment (industry or size only)
    - low: Name/email only (no enrichment)
    """
    
    def __init__(self, apollo_available: bool = True):
        self.apollo_available = apollo_available
        self.enrichment_cache = {}
    
    def enrich_lead(
        self,
        name: str,
        email: str,
        company: str,
        title: str,
        linkedin_url: Optional[str] = None
    ) -> LeadIntelligence:
        """
        Enrich single lead
        
        Process:
        1. Try Apollo.io person enrichment
        2. Try Apollo.io company enrichment
        3. Classify confidence based on data quality
        4. Return LeadIntelligence object
        """
        
        if not self.apollo_available:
            return self._create_basic_lead(name, email, company, title)
        
        # Check cache
        cache_key = f"{email}_{company}"
        if cache_key in self.enrichment_cache:
            return self.enrichment_cache[cache_key]
        
        lead = LeadIntelligence(
            name=name,
            email=email,
            company=company,
            title=title,
            linkedin_url=linkedin_url,
            data_source="apollo_mcp"
        )
        
        # Attempt person enrichment
        person_data = self._enrich_person(email, name, linkedin_url)
        if person_data:
            lead.title = person_data.get("title", lead.title)
            lead.linkedin_url = person_data.get("linkedin_url", lead.linkedin_url)
        
        # Attempt company enrichment
        company_data = self._enrich_company(company)
        if company_data:
            lead.industry = company_data.get("industry")
            lead.company_size = company_data.get("company_size")
            lead.website_url = company_data.get("website_url")
            lead.tech_stack = company_data.get("tech_stack", [])
        
        # Classify confidence
        lead.enrichment_confidence = self._assess_confidence(lead)
        lead.enriched_date = self._get_timestamp()
        
        # Cache result
        self.enrichment_cache[cache_key] = lead
        
        return lead
    
    def _enrich_person(
        self,
        email: str,
        name: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Call Apollo.io people enrichment
        
        Note: This is a placeholder - actual MCP call would happen here
        """
        try:
            # In production, this would call:
            # apollo_io:people_enrichment with email/name/linkedin
            
            # For now, return None (manual implementation required)
            return None
            
        except Exception as e:
            print(f"Apollo person enrichment failed: {e}")
            return None
    
    def _enrich_company(self, company_name: str) -> Optional[Dict]:
        """
        Call Apollo.io organization enrichment
        
        Note: This is a placeholder - actual MCP call would happen here
        """
        try:
            # In production, this would call:
            # apollo_io:organization_enrichment with company name
            
            # For now, return None (manual implementation required)
            return None
            
        except Exception as e:
            print(f"Apollo company enrichment failed: {e}")
            return None
    
    def _assess_confidence(self, lead: LeadIntelligence) -> str:
        """
        Classify enrichment confidence
        
        high: Industry + company_size + tech_stack
        medium: Industry or company_size (but not both)
        low: None of the above
        """
        
        has_industry = bool(lead.industry)
        has_size = bool(lead.company_size)
        has_tech = bool(lead.tech_stack and len(lead.tech_stack) > 0)
        
        if has_industry and has_size:
            if has_tech:
                return "high"
            return "medium"
        
        if has_industry or has_size:
            return "medium"
        
        return "low"
    
    def _create_basic_lead(
        self,
        name: str,
        email: str,
        company: str,
        title: str
    ) -> LeadIntelligence:
        """Fallback when Apollo unavailable"""
        return LeadIntelligence(
            name=name,
            email=email,
            company=company,
            title=title,
            enrichment_confidence="low",
            data_source="manual"
        )
    
    def _get_timestamp(self) -> str:
        """Current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def batch_enrich(
        self,
        leads: List[Dict[str, str]]
    ) -> List[LeadIntelligence]:
        """
        Enrich multiple leads
        
        Input format:
        [
            {"name": "...", "email": "...", "company": "...", "title": "..."},
            ...
        ]
        """
        enriched = []
        
        for lead_data in leads:
            enriched_lead = self.enrich_lead(
                name=lead_data.get("name", ""),
                email=lead_data.get("email", ""),
                company=lead_data.get("company", ""),
                title=lead_data.get("title", ""),
                linkedin_url=lead_data.get("linkedin_url")
            )
            enriched.append(enriched_lead)
        
        return enriched
    
    def export_enriched_leads(
        self,
        leads: List[LeadIntelligence],
        output_path: str
    ):
        """Export enriched leads to JSON"""
        data = [asdict(lead) for lead in leads]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported {len(leads)} enriched leads to {output_path}")
