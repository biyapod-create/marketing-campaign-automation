"""
Campaign Orchestrator
====================
Master controller that executes the tool-first pipeline.

Pipeline:
1. Load leads (manual or Apollo search)
2. Enrich via Apollo.io MCP
3. Route decisions via DecisionRouter
4. Generate messages via MessageGenerator  
5. Export campaign-ready assets
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from .decision_router import DecisionRouter, LeadIntelligence
from .message_generator import MessageGenerator
from .lead_enricher import LeadEnricher


class CampaignOrchestrator:
    """
    End-to-end campaign execution controller
    
    Usage:
        orchestrator = CampaignOrchestrator(campaign_dir)
        orchestrator.run_pipeline(input_leads, output_dir)
    """
    
    def __init__(self, campaign_dir: Path):
        self.campaign_dir = Path(campaign_dir)
        
        # Initialize components
        self.router = DecisionRouter(campaign_dir)
        self.generator = MessageGenerator(self.router.icp_clusters)
        self.enricher = LeadEnricher(apollo_available=True)
        
        # Config
        with open(self.campaign_dir / "campaign_database.json") as f:
            self.config = json.load(f)
    
    def run_pipeline(
        self,
        input_leads: List[Dict[str, str]],
        output_dir: Optional[Path] = None,
        skip_enrichment: bool = False
    ) -> Dict:
        """
        Execute full marketing pipeline
        
        Args:
            input_leads: List of raw lead dicts
            output_dir: Where to save generated emails
            skip_enrichment: Skip Apollo.io calls (use manual data only)
        
        Returns:
            Pipeline results summary
        """
        
        if not output_dir:
            output_dir = self.campaign_dir / "generated_campaigns"
            output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        campaign_output_dir = output_dir / f"campaign_{timestamp}"
        campaign_output_dir.mkdir(exist_ok=True)
        
        print(f"🚀 Starting campaign pipeline...")
        print(f"📊 Input: {len(input_leads)} leads")
        print(f"📁 Output: {campaign_output_dir}")
        print()
        
        # Step 1: Enrich leads
        print("⚡ Step 1: Lead Enrichment")
        if skip_enrichment:
            print("   Skipping Apollo.io enrichment (manual mode)")
            enriched_leads = self._convert_to_lead_intelligence(input_leads)
        else:
            print("   Calling Apollo.io MCP for enrichment...")
            enriched_leads = self.enricher.batch_enrich(input_leads)
        
        print(f"   ✅ Enriched {len(enriched_leads)} leads")
        self._log_enrichment_quality(enriched_leads)
        print()
        
        # Step 2: Route decisions
        print("⚡ Step 2: Decision Routing")
        decisions = self.router.batch_route(enriched_leads)
        print(f"   ✅ Routed {len(decisions)} leads")
        self._log_routing_summary(decisions)
        print()
        
        # Step 3: Generate messages
        print("⚡ Step 3: Message Generation")
        generated_messages = []
        for decision in decisions:
            msg = self.generator.generate_cold_email(decision)
            generated_messages.append({
                "lead": decision.lead,
                "message": msg,
                "decision": decision
            })
        print(f"   ✅ Generated {len(generated_messages)} emails")
        print()
        
        # Step 4: Export assets
        print("⚡ Step 4: Export Campaign Assets")
        self._export_campaign(campaign_output_dir, generated_messages, enriched_leads, decisions)
        print(f"   ✅ Exported to {campaign_output_dir}")
        print()
        
        # Summary
        summary = {
            "timestamp": timestamp,
            "total_leads": len(input_leads),
            "enriched": len(enriched_leads),
            "messages_generated": len(generated_messages),
            "output_directory": str(campaign_output_dir),
            "confidence_distribution": self._get_confidence_distribution(decisions),
            "icp_distribution": self._get_icp_distribution(decisions),
            "angle_distribution": self._get_angle_distribution(decisions)
        }
        
        print("=" * 60)
        print("✅ PIPELINE COMPLETE")
        print("=" * 60)
        print(f"📊 Total Processed: {summary['total_leads']}")
        print(f"📧 Emails Generated: {summary['messages_generated']}")
        print(f"📁 Output Location: {campaign_output_dir}")
        print()
        
        return summary
    
    def _convert_to_lead_intelligence(
        self,
        raw_leads: List[Dict[str, str]]
    ) -> List[LeadIntelligence]:
        """Convert raw lead dicts to LeadIntelligence objects (no enrichment)"""
        
        return [
            LeadIntelligence(
                name=lead.get("name", ""),
                email=lead.get("email", ""),
                company=lead.get("company", ""),
                title=lead.get("title", ""),
                linkedin_url=lead.get("linkedin_url"),
                enrichment_confidence="low",
                data_source="manual"
            )
            for lead in raw_leads
        ]
    
    def _log_enrichment_quality(self, leads: List[LeadIntelligence]):
        """Log enrichment confidence distribution"""
        high = sum(1 for l in leads if l.enrichment_confidence == "high")
        medium = sum(1 for l in leads if l.enrichment_confidence == "medium")
        low = sum(1 for l in leads if l.enrichment_confidence == "low")
        
        print(f"   Confidence: High={high}, Medium={medium}, Low={low}")
    
    def _log_routing_summary(self, decisions):
        """Log routing decision distribution"""
        angles = {}
        for d in decisions:
            angles[d.primary_angle] = angles.get(d.primary_angle, 0) + 1
        
        print("   Angles locked:")
        for angle, count in angles.items():
            print(f"      {angle}: {count}")
    
    def _get_confidence_distribution(self, decisions) -> Dict[str, int]:
        """Get confidence level distribution"""
        dist = {"high": 0, "medium": 0, "low": 0}
        for d in decisions:
            dist[d.confidence] = dist.get(d.confidence, 0) + 1
        return dist
    
    def _get_icp_distribution(self, decisions) -> Dict[str, int]:
        """Get ICP cluster distribution"""
        dist = {}
        for d in decisions:
            dist[d.icp_cluster] = dist.get(d.icp_cluster, 0) + 1
        return dist
    
    def _get_angle_distribution(self, decisions) -> Dict[str, int]:
        """Get messaging angle distribution"""
        dist = {}
        for d in decisions:
            dist[d.primary_angle] = dist.get(d.primary_angle, 0) + 1
        return dist
    
    def _export_campaign(
        self,
        output_dir: Path,
        generated_messages: List[Dict],
        enriched_leads: List[LeadIntelligence],
        decisions
    ):
        """
        Export campaign assets:
        - Individual email files
        - Campaign CSV for bulk upload
        - Decision log for analysis
        - Summary report
        """
        
        # Create subdirectories
        emails_dir = output_dir / "emails"
        emails_dir.mkdir(exist_ok=True)
        
        # Export individual emails
        for idx, item in enumerate(generated_messages, 1):
            lead = item["lead"]
            message = item["message"]
            
            email_filename = f"{idx:03d}_{lead.name.replace(' ', '_')}_{lead.company.replace(' ', '_')}.txt"
            email_path = emails_dir / email_filename
            
            with open(email_path, 'w', encoding='utf-8') as f:
                f.write(f"To: {lead.email}\n")
                f.write(f"Subject: {message.subject_line}\n")
                f.write(f"\n{message.body}\n")
        
        # Export campaign CSV (for email tools)        
        campaign_csv_path = output_dir / "campaign_ready.csv"
        with open(campaign_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "name", "email", "company", "title", "subject_line", "body",
                "icp_cluster", "angle", "confidence", "personalization_points"
            ])
            
            for item in generated_messages:
                lead = item["lead"]
                message = item["message"]
                decision = item["decision"]
                
                writer.writerow([
                    lead.name,
                    lead.email,
                    lead.company,
                    lead.title,
                    message.subject_line,
                    message.body,
                    decision.icp_cluster,
                    decision.primary_angle,
                    decision.confidence,
                    "; ".join(message.personalization_points)
                ])
        
        # Export decision log (for performance tracking)
        decision_log_path = output_dir / "decision_log.json"
        with open(decision_log_path, 'w') as f:
            json.dump([
                {
                    "lead_email": d.lead.email,
                    "lead_company": d.lead.company,
                    "icp_cluster": d.icp_cluster,
                    "primary_angle": d.primary_angle,
                    "funnel_stage": d.funnel_stage,
                    "confidence": d.confidence,
                    "reasoning": d.reasoning
                }
                for d in decisions
            ], f, indent=2)
        
        # Export enriched lead data
        enriched_data_path = output_dir / "enriched_leads.json"
        with open(enriched_data_path, 'w') as f:
            from dataclasses import asdict
            json.dump([asdict(lead) for lead in enriched_leads], f, indent=2)
        
        # Generate summary report
        summary_path = output_dir / "CAMPAIGN_SUMMARY.md"
        with open(summary_path, 'w') as f:
            f.write("# Campaign Generation Summary\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Leads Processed:** {len(generated_messages)}\n\n")
            
            f.write("## Confidence Distribution\n\n")
            conf_dist = self._get_confidence_distribution(decisions)
            for level, count in conf_dist.items():
                f.write(f"- {level.upper()}: {count}\n")
            
            f.write("\n## ICP Cluster Distribution\n\n")
            icp_dist = self._get_icp_distribution(decisions)
            for cluster, count in icp_dist.items():
                f.write(f"- {cluster}: {count}\n")
            
            f.write("\n## Messaging Angle Distribution\n\n")
            angle_dist = self._get_angle_distribution(decisions)
            for angle, count in angle_dist.items():
                f.write(f"- {angle}: {count}\n")
            
            f.write("\n## Files Generated\n\n")
            f.write(f"- Individual emails: `emails/` ({len(generated_messages)} files)\n")
            f.write(f"- Campaign CSV: `campaign_ready.csv`\n")
            f.write(f"- Decision log: `decision_log.json`\n")
            f.write(f"- Enriched data: `enriched_leads.json`\n")
            
            f.write("\n## Next Steps\n\n")
            f.write("1. Review generated emails in `emails/` directory\n")
            f.write("2. Import `campaign_ready.csv` to your email tool\n")
            f.write("3. Send first batch (start with 10-20 for testing)\n")
            f.write("4. Track responses and update campaign history\n")
            f.write("5. Iterate based on performance data\n")
