"""
Message Generator
=================
Converts routing decisions into compliant marketing copy.

Rules:
- Open with situational awareness
- Explain solution as process, not product
- Position as system partner
- Permission-based CTA
- No hype, no emojis, no buzzwords
"""

import os
from typing import Dict, List
from dataclasses import dataclass
from dotenv import load_dotenv
from .decision_router import MessageDecision, ICPCluster

load_dotenv()
SENDER_NAME = os.getenv("SENDER_NAME", "Your Company")
SENDER_PHONE = os.getenv("SENDER_PHONE", "")
SENDER_EMAIL = os.getenv("SMTP_USER", "")


@dataclass
class GeneratedMessage:
    """Output message structure"""
    subject_line: str
    body: str
    angle_used: str
    personalization_points: List[str]
    confidence: str
    internal_notes: str


class MessageGenerator:
    """
    Tool-informed copy generation
    
    Core principle: Evidence → Language
    Never fabricate personalization
    """
    
    def __init__(self, icp_clusters: Dict[str, ICPCluster]):
        self.icp_clusters = icp_clusters
        
        # Angle-specific frameworks
        self.angle_frameworks = {
            "revenue_leakage": {
                "observation": "pattern of credibility gaps affecting client acquisition",
                "mechanism": "professional digital infrastructure",
                "position": "systematic setup process",
                "cta_frame": "exploratory"
            },
            "operational_inefficiency": {
                "observation": "manual processes consuming operational capacity",
                "mechanism": "integrated automation layer",
                "position": "workflow optimization partner",
                "cta_frame": "diagnostic"
            },
            "scalability_ceiling": {
                "observation": "current infrastructure limiting growth capacity",
                "mechanism": "scalable foundation systems",
                "position": "growth infrastructure partner",
                "cta_frame": "planning"
            }
        }
    
    def generate_cold_email(self, decision: MessageDecision) -> GeneratedMessage:
        """
        Generate cold outreach email from routing decision
        
        Structure:
        1. Situational awareness (not introduction)
        2. Observable problem (from angle)
        3. Solution as process (not product)
        4. Permission-based CTA
        """
        
        lead = decision.lead
        cluster = self.icp_clusters.get(decision.icp_cluster)
        framework = self.angle_frameworks.get(decision.primary_angle)
        
        # Build personalization context
        personalization = []
        context_depth = "shallow"
        
        if lead.industry and decision.confidence == "high":
            context_depth = "medium"
            personalization.append(f"industry: {lead.industry}")
            
        if lead.tech_stack:
            context_depth = "deep"
            personalization.append(f"tech stack: {', '.join(lead.tech_stack[:2])}")
        
        # Generate subject line (never hype)
        subject_line = self._generate_subject(decision, context_depth)
        
        # Generate body
        body = self._generate_body(decision, cluster, framework, context_depth)
        
        internal_notes = f"""
        Decision Confidence: {decision.confidence}
        Personalization Depth: {context_depth}
        ICP Cluster: {decision.icp_cluster}
        Primary Angle: {decision.primary_angle}
        Data Source: {lead.data_source}
        """
        
        return GeneratedMessage(
            subject_line=subject_line,
            body=body,
            angle_used=decision.primary_angle,
            personalization_points=personalization,
            confidence=decision.confidence,
            internal_notes=internal_notes.strip()
        )
    
    def _generate_subject(self, decision: MessageDecision, depth: str) -> str:
        """Subject lines: clear, not clever"""
        
        angle = decision.primary_angle
        cluster = decision.icp_cluster
        
        # Conservative subjects for cold stage
        subjects = {
            ("revenue_leakage", "early_stage_startup"): "Digital infrastructure question",
            ("revenue_leakage", "digitizing_smb"): "Online presence setup",
            ("operational_inefficiency", "service_business"): "Booking system question",
            ("operational_inefficiency", "ecommerce_startup"): "Order management question",
            ("scalability_ceiling", "solopreneur"): "Client intake infrastructure"
        }
        
        key = (angle, cluster)
        return subjects.get(key, "Digital foundation setup")
    
    def _generate_body(
        self,
        decision: MessageDecision,
        cluster: ICPCluster,
        framework: Dict,
        depth: str
    ) -> str:
        """
        Body generation following structural rules
        
        Never:
        - Start with "I came across..."
        - Use template variables without data
        - Make fabricated claims
        - Use urgency manipulation
        """
        
        lead = decision.lead
        angle = decision.primary_angle
        
        # Section 1: Situational awareness (cluster-specific)
        situation = self._build_situation(cluster, lead, depth)
        
        # Section 2: Observable problem (angle-specific)
        problem = self._build_problem(angle, cluster)
        
        # Section 3: Solution as process
        solution = self._build_solution(angle)
        
        # Section 4: Permission CTA
        cta = self._build_cta(decision.funnel_stage, framework.get("cta_frame", "exploratory"))
        
        # Assemble
        body = f"""{situation}

{problem}

{solution}

{cta}

{SENDER_NAME}
{SENDER_PHONE}
{SENDER_EMAIL}"""
        
        return body.strip()
    
    def _build_situation(self, cluster: ICPCluster, lead, depth: str) -> str:
        """Open with segment-level observation"""
        
        # NEVER fabricate specific company knowledge
        # Use cluster patterns instead
        
        situations = {
            "early_stage_startup": f"Hi {lead.name},\n\nMost early-stage founders hit a credibility gap when talking to investors or enterprise clients—the product might be solid, but the digital presence doesn't match the pitch.",
            
            "digitizing_smb": f"Hi {lead.name},\n\nMany established businesses find themselves losing ground to competitors who invested in professional digital infrastructure. The gap compounds over time.",
            
            "solopreneur": f"Hi {lead.name},\n\nIndependent consultants often reach a ceiling where referrals slow down and premium rates become hard to justify without a professional presence that matches the expertise.",
            
            "ecommerce_startup": f"Hi {lead.name},\n\nSellers who start on Instagram or WhatsApp eventually hit operational limits—manual order tracking, payment collection through DMs, no inventory visibility.",
            
            "service_business": f"Hi {lead.name},\n\nService businesses typically spend significant time managing bookings through phone calls and WhatsApp, time that could go toward actual service delivery.",
            
            "ngo_nonprofit": f"Hi {lead.name},\n\nNonprofits often struggle to scale donor reach beyond their immediate network, especially when grant applications expect a professional web presence and online donation capability."
        }
        
        return situations.get(cluster.cluster_name.lower().replace(" ", "_").replace("&", "").replace("-", "_"), 
                             f"Hi {lead.name},\n\nMany businesses in your industry face infrastructure gaps that limit growth.")
    
    def _build_problem(self, angle: str, cluster: ICPCluster) -> str:
        """State problem as observable pattern"""
        
        # Pull from cluster pain points
        if not cluster or not cluster.common_pains:
            return "This typically shows up as missed opportunities and operational friction."
        
        # Use top 1-2 pains only
        primary_pain = cluster.common_pains[0]
        
        return f"This typically shows up as: {primary_pain.lower()}"
    
    def _build_solution(self, angle: str) -> str:
        """Explain solution as process, not product"""
        
        solutions = {
            "revenue_leakage": """We work with businesses to build complete digital foundations—not templates, but custom infrastructure: business-ready websites, professional email systems, payment integration, and brand identity work.

The process takes 7-14 days and handles the full technical setup so you can focus on the business side.""",
            
            "operational_inefficiency": """We build integrated systems that automate the repetitive parts: online booking, payment collection, client intake, order management—depending on what's consuming the most operational capacity.

The setup process takes 7-14 days and includes the complete technical infrastructure.""",
            
            "scalability_ceiling": """We handle the infrastructure buildout: professional web presence, automated client intake, payment systems, brand positioning—the technical foundation needed to scale beyond the current ceiling.

The process takes 7-14 days and delivers production-ready systems."""
        }
        
        return solutions.get(angle, solutions["revenue_leakage"])
    
    def _build_cta(self, funnel_stage: str, cta_frame: str) -> str:
        """Permission-based CTA, never pushy"""
        
        if funnel_stage == "cold":
            return "Would a 15-minute call next week make sense to walk through your specific situation and see if this approach fits?"
        elif funnel_stage == "warm":
            return "Would you be open to reconnecting for a brief call to explore this?"
        else:  # hot
            return "Would you like to schedule time to discuss implementation specifics?"
