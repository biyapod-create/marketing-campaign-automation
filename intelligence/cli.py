"""
Marketing Intelligence CLI
==========================
Command-line interface for tool-first marketing execution.

Commands:
- generate: Run full pipeline (enrich → route → generate)
- enrich: Enrich leads only
- performance: View campaign performance
- insights: Get iteration recommendations
"""

import argparse
import json
import sys
from pathlib import Path

# Add intelligence package to path
campaign_dir = Path(__file__).parent.parent
sys.path.insert(0, str(campaign_dir))

from intelligence.campaign_orchestrator import CampaignOrchestrator
from intelligence.performance_tracker import PerformanceTracker
from intelligence.lead_enricher import LeadEnricher


def load_leads_from_csv(csv_path: Path):
    """Load leads from CSV file"""
    import csv
    
    leads = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('email'):  # Skip empty rows
                leads.append({
                    "name": row.get("name", ""),
                    "email": row.get("email", ""),
                    "company": row.get("company", ""),
                    "title": row.get("title", ""),
                    "linkedin_url": row.get("linkedin_url", "")
                })
    
    return leads


def cmd_generate(args):
    """Generate campaign from leads"""
    
    print("=" * 60)
    print("CAMPAIGN GENERATION")
    print("=" * 60)
    print()
    
    # Load leads
    if args.leads_csv:
        leads = load_leads_from_csv(Path(args.leads_csv))
    elif args.leads_json:
        with open(args.leads_json) as f:
            leads = json.load(f)
    else:
        print("❌ Error: Must provide either --leads-csv or --leads-json")
        return
    
    print(f"📊 Loaded {len(leads)} leads")
    print()
    
    # Run pipeline
    orchestrator = CampaignOrchestrator(campaign_dir)
    
    output_dir = Path(args.output) if args.output else None
    skip_enrichment = args.skip_enrichment
    
    summary = orchestrator.run_pipeline(
        input_leads=leads,
        output_dir=output_dir,
        skip_enrichment=skip_enrichment
    )
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2))


def cmd_enrich(args):
    """Enrich leads only (no message generation)"""
    
    print("=" * 60)
    print("LEAD ENRICHMENT")
    print("=" * 60)
    print()
    
    # Load leads
    if args.leads_csv:
        leads = load_leads_from_csv(Path(args.leads_csv))
    elif args.leads_json:
        with open(args.leads_json) as f:
            leads = json.load(f)
    else:
        print("❌ Error: Must provide either --leads-csv or --leads-json")
        return
    
    print(f"📊 Loaded {len(leads)} leads")
    print()
    
    # Enrich
    enricher = LeadEnricher(apollo_available=not args.manual_only)
    enriched = enricher.batch_enrich(leads)
    
    print(f"✅ Enriched {len(enriched)} leads")
    print()
    
    # Export
    output_path = Path(args.output) if args.output else campaign_dir / "enriched_leads.json"
    enricher.export_enriched_leads(enriched, str(output_path))
    
    print(f"💾 Saved to: {output_path}")


def cmd_performance(args):
    """View campaign performance"""
    
    print("=" * 60)
    print("CAMPAIGN PERFORMANCE")
    print("=" * 60)
    print()
    
    tracker = PerformanceTracker(campaign_dir)
    performances = tracker.get_campaign_performance(args.campaign_id)
    
    if not performances:
        print("📊 No performance data yet")
        print()
        print("💡 Send your first campaign and log results using:")
        print("   tracker.log_send()")
        print("   tracker.log_open()")
        print("   tracker.log_reply()")
        return
    
    print(f"📊 Found {len(performances)} campaign segments")
    print()
    
    for perf in performances:
        print(f"Campaign: {perf.campaign_id}")
        print(f"Angle: {perf.angle}")
        print(f"ICP Segment: {perf.icp_segment}")
        print(f"Total Sent: {perf.total_sent}")
        print(f"Open Rate: {perf.open_rate:.1%}")
        print(f"Reply Rate: {perf.reply_rate:.1%}")
        print(f"Conversion Rate: {perf.conversion_rate:.1%}")
        print(f"Meetings Booked: {perf.meetings_booked}")
        print("-" * 60)
    
    print()


def cmd_insights(args):
    """Get performance insights and iteration recommendations"""
    
    print("=" * 60)
    print("CAMPAIGN INSIGHTS")
    print("=" * 60)
    print()
    
    tracker = PerformanceTracker(campaign_dir)
    insights = tracker.generate_insights()
    
    if insights.get("status") == "No data yet":
        print("📊 No data available yet")
        print()
        print("💡 Send your first campaign to start building intelligence")
        return
    
    print(f"📊 Total Campaigns: {insights['total_campaigns']}")
    print(f"📧 Total Sends: {insights['total_sends']}")
    print()
    
    if insights['best_performers']:
        print("🏆 BEST PERFORMERS:")
        for bp in insights['best_performers']:
            print(f"   {bp['angle']} → {bp['icp_segment']}")
            print(f"   Reply Rate: {bp['reply_rate']} (n={bp['sample_size']})")
            print()
    
    if insights['underperformers']:
        print("⚠️  UNDERPERFORMERS:")
        for up in insights['underperformers']:
            print(f"   {up['issue']}: {up['angle']} → {up['icp_segment']}")
            print(f"   Diagnosis: {up['diagnosis']}")
            print()
    
    if insights['iteration_recommendations']:
        print("💡 RECOMMENDATIONS:")
        for rec in insights['iteration_recommendations']:
            print(f"   • {rec}")
        print()
    
    # Export for router
    if args.export:
        export_path = campaign_dir / "intelligence" / "campaign_history.json"
        tracker.export_for_router(export_path)


def main():
    parser = argparse.ArgumentParser(
        description="Tool-First Marketing Intelligence System"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate campaign')
    gen_parser.add_argument('--leads-csv', help='Path to leads CSV file')
    gen_parser.add_argument('--leads-json', help='Path to leads JSON file')
    gen_parser.add_argument('--output', help='Output directory')
    gen_parser.add_argument('--skip-enrichment', action='store_true', 
                           help='Skip Apollo enrichment (manual mode)')
    
    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Enrich leads only')
    enrich_parser.add_argument('--leads-csv', help='Path to leads CSV file')
    enrich_parser.add_argument('--leads-json', help='Path to leads JSON file')
    enrich_parser.add_argument('--output', help='Output JSON path')
    enrich_parser.add_argument('--manual-only', action='store_true',
                              help='Skip Apollo (manual enrichment only)')
    
    # Performance command
    perf_parser = subparsers.add_parser('performance', help='View performance')
    perf_parser.add_argument('--campaign-id', help='Filter by campaign ID')
    
    # Insights command
    insights_parser = subparsers.add_parser('insights', help='Get insights')
    insights_parser.add_argument('--export', action='store_true',
                                help='Export campaign history for router')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'enrich':
        cmd_enrich(args)
    elif args.command == 'performance':
        cmd_performance(args)
    elif args.command == 'insights':
        cmd_insights(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
