"""
Allennetic Marketing Campaign - Master Orchestrator
Natural language interface to the entire campaign system.

USAGE EXAMPLES:
    >>> from master_orchestrator import CampaignOrchestrator
    >>> campaign = CampaignOrchestrator()
    
    # Find leads using natural language
    >>> campaign.execute("find 30 SMEs in Abuja that need websites")
    
    # Check campaign status
    >>> campaign.status()
    
    # Generate and send emails
    >>> campaign.execute("send emails to all new leads")
"""

import json
import os
import sys
import glob
from datetime import datetime
from typing import Dict, List, Optional

# Add intelligence directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'intelligence'))

try:
    from intelligence.apollo_semantic_router import ApolloSemanticRouter
    from intelligence.email_sender import EmailSender
except ImportError:
    from apollo_semantic_router import ApolloSemanticRouter
    from email_sender import EmailSender


class CampaignOrchestrator:
    """
    Master orchestrator for Allennetic's marketing campaign.
    
    This is your single entry point for the entire campaign system.
    Handles: lead finding → enrichment → email generation → sending → tracking
    """
    
    def __init__(self, campaign_dir: str = None):
        if campaign_dir is None:
            campaign_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.campaign_dir = campaign_dir
        self.router = ApolloSemanticRouter()
        self.email_sender = EmailSender()
        
        # Load configuration
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load campaign configuration"""
        config_path = os.path.join(self.campaign_dir, "campaign_database.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            return {}
    
    def execute(self, natural_command: str) -> Dict:
        """
        Main execution method. Handles any natural language campaign command.
        
        Args:
            natural_command: Natural language instruction
            
        Examples:
            "find 30 SMEs in Abuja that need websites"
            "send emails to all new leads"
            "check campaign status"
            "show me today's responses"
        """
        command_lower = natural_command.lower()
        
        # Route to appropriate handler
        if any(word in command_lower for word in ['find', 'search', 'get', 'locate']):
            return self._handle_lead_finding(natural_command)
        
        elif any(word in command_lower for word in ['send email', 'email', 'outreach']):
            return self._handle_email_sending(natural_command)
        
        elif any(word in command_lower for word in ['status', 'progress', 'stats']):
            return self._handle_status_check()
        
        elif any(word in command_lower for word in ['response', 'reply', 'replies']):
            return self._handle_response_check()
        
        else:
            return {
                "error": "Command not recognized",
                "suggestion": "Try: 'find 30 SMEs in Abuja' or 'check campaign status'",
                "command": natural_command
            }
    
    def _handle_lead_finding(self, query: str) -> Dict:
        """Handle lead finding requests"""
        
        # Parse the query
        tool_name, params = self.router.route(query)
        
        # Show what will be done
        explanation = self.router.explain_routing(query)
        
        return {
            "action": "lead_finding",
            "query": query,
            "interpretation": explanation,
            "apollo_tool": tool_name,
            "parameters": params,
            "next_step": "Ready to call Apollo MCP. Invoke the tool to execute.",
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_email_sending(self, command: str) -> Dict:
        """Handle email sending requests"""
        command_lower = command.lower()

        # Test connection
        if "test" in command_lower and "connect" in command_lower:
            return self.email_sender.test_connection()

        # Send single email — expect JSON payload in command or via args
        if "single" in command_lower:
            return {"action": "send_single", "note": "Use email_sender.send_email(to, subject, body) directly."}

        # Batch send from campaign CSV
        csv_candidates = [
            os.path.join(self.campaign_dir, "generated_campaigns"),
            os.path.join(self.campaign_dir, "leads"),
        ]
        dry_run = "live" not in command_lower  # default to dry_run unless 'live' specified
        limit = 10

        # Find most recent campaign_ready.csv
        pattern = os.path.join(self.campaign_dir, "**", "campaign_ready.csv")
        csvs = sorted(glob.glob(pattern, recursive=True), key=os.path.getmtime, reverse=True)

        if not csvs:
            return {"action": "email_sending", "status": "no_csv", "note": "No campaign_ready.csv found. Run the pipeline first."}

        latest_csv = csvs[0]
        result = self.email_sender.send_batch_from_csv(latest_csv, limit=limit, dry_run=dry_run)
        result["csv_used"] = latest_csv
        result["action"] = "email_sending"
        return result
    
    def _handle_status_check(self) -> Dict:
        """Check campaign status"""
        progress = self.config.get("progress", {})
        
        return {
            "action": "status_check",
            "campaign_name": self.config.get("campaign_info", {}).get("name", "Unknown"),
            "status": self.config.get("campaign_info", {}).get("status", "Unknown"),
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        }
    
    def _handle_response_check(self) -> Dict:
        """Check for responses"""
        return {
            "action": "response_check",
            "status": "not_implemented",
            "note": "Response tracking will be integrated next"
        }
    
    def status(self) -> Dict:
        """Quick status check"""
        return self._handle_status_check()
    
    def help(self) -> str:
        """Show available commands"""
        return """
ALLENNETIC CAMPAIGN ORCHESTRATOR - COMMAND REFERENCE

LEAD FINDING:
  campaign.execute("find 30 SMEs in Abuja that need websites")
  campaign.execute("find 50 startups in Lagos")
  campaign.execute("get 20 founders in Nigeria")

STATUS CHECKING:
  campaign.status()
  campaign.execute("check campaign status")

EMAIL OPERATIONS (Coming soon):
  campaign.execute("send emails to new leads")
  campaign.execute("follow up with leads")

RESPONSE TRACKING (Coming soon):
  campaign.execute("show responses")
  campaign.execute("check for new replies")

ADVANCED:
  result = campaign.execute("your command here")
  print(json.dumps(result, indent=2))
"""


# CLI Interface
if __name__ == "__main__":
    campaign = CampaignOrchestrator()
    
    if len(sys.argv) < 2:
        print(campaign.help())
        sys.exit(0)
    
    # Execute command from CLI
    command = " ".join(sys.argv[1:])
    result = campaign.execute(command)
    
    print(json.dumps(result, indent=2))
