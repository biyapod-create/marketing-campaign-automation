"""
Marketing Decision Router
=========================
Tool-first marketing agent that makes decisions before writing.

Core Principle: Tools → Evidence → Language
"""

import json
import sqlite3
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class LeadIntelligence:
    """Enriched lead data from tools"""
    company: str
    name: str
    email: str
    title: str
    
    # Enrichment data
    industry: Optional[str] = None
    company_size: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    hiring_signals: Optional[bool] = None
    growth_indicators: Optional[List[str]] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    # Confidence scoring
    enrichment_confidence: Literal["high", "medium", "low"] = "low"
    data_source: str = "manual"
    enriched_date: Optional[str] = None


@dataclass
class ICPCluster:
    """Market segment patterns"""
    cluster_name: str
    common_pains: List[str]
    objections: List[str]
    decision_drivers: List[str]
    typical_size: str
    typical_industry: str
    confidence: Literal["high", "medium", "low"] = "medium"


@dataclass
class CampaignHistory:
    """Historical performance data"""
    angle: str
    icp_segment: str
    open_rate: float
    reply_rate: float
    conversion_rate: float
    sample_size: int
    avg_time_to_reply: Optional[float] = None
    common_objections: Optional[List[str]] = None


@dataclass
class MessageDecision:
    """Final routing decision"""
    lead: LeadIntelligence
    task_type: Literal["prospecting", "inbound", "retention", "positioning"]
    funnel_stage: Literal["cold", "warm", "hot"]
    primary_angle: Literal[
        "revenue_leakage", 
        "operational_inefficiency",
        "technical_instability",
        "conversion_dropoff",
        "scalability_ceiling",
        "risk_mitigation"
    ]
    icp_cluster: str
    confidence: Literal["high", "medium", "low"]
    reasoning: str
    

class DecisionRouter:
    """
    Tool-First Marketing Decision Engine
    
    Responsibilities:
    1. Classify task type and funnel stage
    2. Route to appropriate tools
    3. Lock messaging angle based on data
    4. Generate context-aware decisions
    """
    
    def __init__(self, campaign_dir: Path):
        self.campaign_dir = Path(campaign_dir)
        self.db_path = self.campaign_dir / "allennetic-lead-system" / "allennetic_leads.db"
        self.config_path = self.campaign_dir / "campaign_database.json"
        
        # Load configurations
        with open(self.config_path) as f:
            self.config = json.load(f)
            
        # ICP Clusters (Nigerian market specific)
        self.icp_clusters = self._load_icp_clusters()
        
        # Campaign history (empty initially, will build over time)
        self.campaign_history: List[CampaignHistory] = []
        
    def _load_icp_clusters(self) -> Dict[str, ICPCluster]:
        """Load market segment intelligence"""
        return {
            "early_stage_startup": ICPCluster(
                cluster_name="Early-stage Startups",
                common_pains=[
                    "No credible digital presence hurts investor conversations",
                    "Using personal email/WhatsApp looks unprofessional to clients",
                    "Can't accept payments without proper infrastructure",
                    "No clear brand identity makes marketing harder"
                ],
                objections=[
                    "Too expensive for current stage",
                    "Can use Wix/WordPress myself",
                    "Need product-market fit first"
                ],
                decision_drivers=[
                    "Speed to market",
                    "Professional appearance to investors/clients",
                    "All-in-one solution vs. piecing things together"
                ],
                typical_size="1-5 employees",
                typical_industry="Tech, SaaS, Consulting",
                confidence="high"
            ),
            
            "digitizing_smb": ICPCluster(
                cluster_name="Businesses Going Digital",
                common_pains=[
                    "Losing customers to competitors with professional websites",
                    "Can't reach customers beyond immediate network",
                    "Manual processes eating up time",
                    "No online payment = missed sales"
                ],
                objections=[
                    "Website won't bring customers",
                    "Current system works fine",
                    "Don't understand tech"
                ],
                decision_drivers=[
                    "Competitors already online",
                    "Customer expectations changing",
                    "Revenue ceiling reached with current approach"
                ],
                typical_size="5-20 employees",
                typical_industry="Retail, Services, Healthcare",
                confidence="high"
            ),
            
            "solopreneur": ICPCluster(
                cluster_name="Solopreneurs & Freelancers",
                common_pains=[
                    "Can't charge premium rates without professional presence",
                    "Spending time on admin instead of client work",
                    "Hard to scale beyond word-of-mouth",
                    "Competing with established players"
                ],
                objections=[
                    "Can't afford it yet",
                    "Social media is enough",
                    "Too complicated to maintain"
                ],
                decision_drivers=[
                    "Want to increase rates",
                    "Need to appear established",
                    "Want automated client intake"
                ],
                typical_size="1 person",
                typical_industry="Consulting, Creative, Coaching",
                confidence="high"
            ),
            
            "ecommerce_startup": ICPCluster(
                cluster_name="E-commerce Sellers",
                common_pains=[
                    "Instagram/WhatsApp-only sales limiting growth",
                    "Can't track inventory or orders properly",
                    "Payment collection is manual and risky",
                    "No customer data for retargeting"
                ],
                objections=[
                    "Social media drives all sales already",
                    "Shopify/WooCommerce too complex",
                    "Payment gateways expensive"
                ],
                decision_drivers=[
                    "Want to scale beyond DMs",
                    "Need proper order management",
                    "Want automated checkout"
                ],
                typical_size="1-10 employees",
                typical_industry="E-commerce, Fashion, Beauty",
                confidence="high"
            ),
            
            "service_business": ICPCluster(
                cluster_name="Service Businesses",
                common_pains=[
                    "Bookings happening via phone/WhatsApp is inefficient",
                    "No professional image hurts premium pricing",
                    "Can't showcase portfolio/work properly",
                    "Losing customers to more modern competitors"
                ],
                objections=[
                    "Customers prefer calling",
                    "Don't need fancy website",
                    "Location-based business"
                ],
                decision_drivers=[
                    "Want to reduce phone time",
                    "Want to charge more",
                    "Need to look more professional"
                ],
                typical_size="3-15 employees",
                typical_industry="Salons, Clinics, Restaurants, Studios",
                confidence="high"
            ),
            
            "ngo_nonprofit": ICPCluster(
                cluster_name="NGOs & Nonprofits",
                common_pains=[
                    "Hard to attract donors without professional presence",
                    "Can't accept online donations easily",
                    "No way to showcase impact/results",
                    "Volunteers/supporters can't easily share mission"
                ],
                objections=[
                    "Limited budget",
                    "Don't have tech skills to maintain",
                    "Donors give offline anyway"
                ],
                decision_drivers=[
                    "Grant applications require web presence",
                    "Younger donors expect online giving",
                    "Need to reach beyond local network"
                ],
                typical_size="2-20 employees",
                typical_industry="Nonprofit, Social Enterprise",
                confidence="medium"
            )
        }
    
    def classify_lead(self, lead: LeadIntelligence) -> str:
        """Map lead to ICP cluster"""
        
        # Use enrichment data if available
        if lead.enrichment_confidence == "high":
            if lead.company_size and "1-5" in lead.company_size:
                if lead.industry and any(x in lead.industry.lower() for x in ["tech", "saas", "software"]):
                    return "early_stage_startup"
                    
            if lead.company_size and any(x in lead.company_size for x in ["5-20", "10-50"]):
                if lead.industry and any(x in lead.industry.lower() for x in ["retail", "service", "health"]):
                    return "digitizing_smb"
                    
        # Fallback to title-based classification
        title_lower = lead.title.lower()
        
        if any(x in title_lower for x in ["founder", "ceo"]) and lead.company_size == "1":
            return "solopreneur"
            
        if any(x in title_lower for x in ["ecommerce", "store", "shop"]):
            return "ecommerce_startup"
            
        if any(x in title_lower for x in ["director", "manager", "owner"]):
            if any(x in (lead.company or "").lower() for x in ["salon", "clinic", "restaurant", "studio"]):
                return "service_business"
                
        # Default to most common segment
        return "digitizing_smb"
    
    def determine_funnel_stage(self, lead: LeadIntelligence) -> Literal["cold", "warm", "hot"]:
        """Infer funnel temperature from interaction history"""
        
        # Check database for previous interactions
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) as interaction_count,
                       MAX(sent_at) as last_interaction,
                       reply_received
                FROM emails
                WHERE recipient_email = ?
            """, (lead.email,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] > 0:
                if result[2]:  # Has replied
                    return "hot"
                else:  # Contacted but no reply
                    return "warm"
                    
        except Exception:
            pass  # DB doesn't exist yet or no history
            
        return "cold"
    
    def select_angle(
        self,
        icp_cluster: str,
        funnel_stage: str,
        lead: LeadIntelligence
    ) -> Tuple[str, str]:
        """
        Lock primary messaging angle based on ICP + funnel stage + history
        
        Returns: (angle, reasoning)
        """
        
        cluster = self.icp_clusters.get(icp_cluster)
        if not cluster:
            return ("revenue_leakage", "Default angle: no cluster match")
            
        # Check campaign history for this cluster (if exists)
        relevant_history = [
            h for h in self.campaign_history 
            if h.icp_segment == icp_cluster and h.sample_size >= 10
        ]
        
        if relevant_history:
            # Historical performance wins
            best_performer = max(relevant_history, key=lambda x: x.reply_rate)
            return (
                best_performer.angle,
                f"Historical best: {best_performer.reply_rate:.1%} reply rate from {best_performer.sample_size} sends"
            )
        
        # No history: Use ICP-specific pain mapping
        angle_map = {
            "early_stage_startup": (
                "revenue_leakage",
                "No credible digital presence hurts investor conversations and client trust"
            ),
            "digitizing_smb": (
                "revenue_leakage",
                "Losing customers to competitors with professional online presence"
            ),
            "solopreneur": (
                "scalability_ceiling",
                "Can't charge premium rates or scale beyond word-of-mouth without professional setup"
            ),
            "ecommerce_startup": (
                "operational_inefficiency",
                "Manual Instagram/WhatsApp sales process limiting growth and creating order chaos"
            ),
            "service_business": (
                "operational_inefficiency",
                "Phone/WhatsApp booking system eating time that should go to customers"
            ),
            "ngo_nonprofit": (
                "revenue_leakage",
                "Hard to attract donors and accept online donations without professional presence"
            )
        }
        
        return angle_map.get(icp_cluster, ("revenue_leakage", "Default angle"))
    
    def route_decision(self, lead: LeadIntelligence) -> MessageDecision:
        """
        Main decision routing logic
        
        Flow:
        1. Classify task type (always prospecting for cold outbound)
        2. Determine funnel temperature
        3. Map to ICP cluster
        4. Select angle based on data
        5. Return decision context
        """
        
        # Step 1: Task type (for now, always prospecting)
        task_type = "prospecting"
        
        # Step 2: Funnel stage
        funnel_stage = self.determine_funnel_stage(lead)
        
        # Step 3: ICP cluster
        icp_cluster = self.classify_lead(lead)
        
        # Step 4: Select angle
        primary_angle, angle_reasoning = self.select_angle(icp_cluster, funnel_stage, lead)
        
        # Step 5: Confidence assessment
        confidence = "high" if lead.enrichment_confidence == "high" else "medium"
        if not lead.industry and not lead.company_size:
            confidence = "low"
        
        reasoning = f"""
        ICP Cluster: {icp_cluster}
        Funnel Stage: {funnel_stage}
        Primary Angle: {primary_angle}
        Angle Reasoning: {angle_reasoning}
        Data Confidence: {confidence}
        Enrichment Source: {lead.data_source}
        """.strip()
        
        return MessageDecision(
            lead=lead,
            task_type=task_type,
            funnel_stage=funnel_stage,
            primary_angle=primary_angle,
            icp_cluster=icp_cluster,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def batch_route(self, leads: List[LeadIntelligence]) -> List[MessageDecision]:
        """Process multiple leads"""
        return [self.route_decision(lead) for lead in leads]
