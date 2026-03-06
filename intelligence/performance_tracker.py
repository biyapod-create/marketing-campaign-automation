"""
Performance Tracker
==================
Tracks campaign results and builds historical intelligence.

Responsibilities:
- Log email sends, opens, replies
- Calculate performance metrics
- Build campaign history for DecisionRouter
- Identify iteration opportunities
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CampaignPerformance:
    """Campaign performance metrics"""
    campaign_id: str
    angle: str
    icp_segment: str
    total_sent: int
    opens: int
    replies: int
    positive_replies: int
    meetings_booked: int
    
    @property
    def open_rate(self) -> float:
        return (self.opens / self.total_sent) if self.total_sent > 0 else 0.0
    
    @property
    def reply_rate(self) -> float:
        return (self.replies / self.total_sent) if self.total_sent > 0 else 0.0
    
    @property
    def conversion_rate(self) -> float:
        return (self.meetings_booked / self.total_sent) if self.total_sent > 0 else 0.0


class PerformanceTracker:
    """
    Campaign performance tracking and analysis
    
    Usage:
        tracker = PerformanceTracker(campaign_dir)
        tracker.log_send(email, decision)
        tracker.log_reply(email, sentiment)
        tracker.generate_insights()
    """
    
    def __init__(self, campaign_dir: Path):
        self.campaign_dir = Path(campaign_dir)
        self.db_path = self.campaign_dir / "intelligence" / "performance.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize performance tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sends table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                lead_email TEXT NOT NULL,
                lead_company TEXT,
                subject_line TEXT,
                icp_cluster TEXT,
                primary_angle TEXT,
                funnel_stage TEXT,
                confidence TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Opens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                send_id INTEGER,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (send_id) REFERENCES sends(id)
            )
        """)
        
        # Replies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                send_id INTEGER,
                sentiment TEXT CHECK(sentiment IN ('positive', 'negative', 'neutral')),
                reply_text TEXT,
                replied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (send_id) REFERENCES sends(id)
            )
        """)
        
        # Meetings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                send_id INTEGER,
                booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (send_id) REFERENCES sends(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_send(
        self,
        campaign_id: str,
        lead_email: str,
        lead_company: str,
        subject_line: str,
        icp_cluster: str,
        primary_angle: str,
        funnel_stage: str,
        confidence: str
    ) -> int:
        """Log email send"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sends (
                campaign_id, lead_email, lead_company, subject_line,
                icp_cluster, primary_angle, funnel_stage, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            campaign_id, lead_email, lead_company, subject_line,
            icp_cluster, primary_angle, funnel_stage, confidence
        ))
        
        send_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return send_id
    
    def log_open(self, send_id: int):
        """Log email open"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO opens (send_id) VALUES (?)", (send_id,))
        conn.commit()
        conn.close()
    
    def log_reply(
        self,
        send_id: int,
        sentiment: str,
        reply_text: Optional[str] = None
    ):
        """Log email reply with sentiment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO replies (send_id, sentiment, reply_text)
            VALUES (?, ?, ?)
        """, (send_id, sentiment, reply_text))
        
        conn.commit()
        conn.close()
    
    def log_meeting(self, send_id: int):
        """Log meeting booked"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO meetings (send_id) VALUES (?)", (send_id,))
        conn.commit()
        conn.close()
    
    def get_campaign_performance(
        self,
        campaign_id: Optional[str] = None
    ) -> List[CampaignPerformance]:
        """Get performance metrics by campaign/angle/ICP"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                s.campaign_id,
                s.primary_angle,
                s.icp_cluster,
                COUNT(DISTINCT s.id) as total_sent,
                COUNT(DISTINCT o.id) as opens,
                COUNT(DISTINCT r.id) as replies,
                COUNT(DISTINCT CASE WHEN r.sentiment = 'positive' THEN r.id END) as positive_replies,
                COUNT(DISTINCT m.id) as meetings
            FROM sends s
            LEFT JOIN opens o ON s.id = o.send_id
            LEFT JOIN replies r ON s.id = r.send_id
            LEFT JOIN meetings m ON s.id = m.send_id
        """
        
        if campaign_id:
            query += " WHERE s.campaign_id = ?"
            cursor.execute(query + " GROUP BY s.campaign_id, s.primary_angle, s.icp_cluster", (campaign_id,))
        else:
            cursor.execute(query + " GROUP BY s.campaign_id, s.primary_angle, s.icp_cluster")
        
        results = []
        for row in cursor.fetchall():
            results.append(CampaignPerformance(
                campaign_id=row[0],
                angle=row[1],
                icp_segment=row[2],
                total_sent=row[3],
                opens=row[4],
                replies=row[5],
                positive_replies=row[6],
                meetings_booked=row[7]
            ))
        
        conn.close()
        return results
    
    def generate_insights(self) -> Dict:
        """
        Generate actionable insights from performance data
        
        Returns diagnosis framework:
        - What's working
        - What's failing
        - Iteration recommendations
        """
        performances = self.get_campaign_performance()
        
        if not performances:
            return {"status": "No data yet", "recommendation": "Send first batch"}
        
        insights = {
            "total_campaigns": len(set(p.campaign_id for p in performances)),
            "total_sends": sum(p.total_sent for p in performances),
            "best_performers": [],
            "underperformers": [],
            "iteration_recommendations": []
        }
        
        # Identify best performers (reply rate > 5%)
        for perf in performances:
            if perf.reply_rate > 0.05 and perf.total_sent >= 10:
                insights["best_performers"].append({
                    "angle": perf.angle,
                    "icp_segment": perf.icp_segment,
                    "reply_rate": f"{perf.reply_rate:.1%}",
                    "sample_size": perf.total_sent
                })
        
        # Identify underperformers (open rate < 20% or reply rate < 1%)
        for perf in performances:
            if perf.total_sent >= 20:
                if perf.open_rate < 0.20:
                    insights["underperformers"].append({
                        "issue": "Low open rate",
                        "angle": perf.angle,
                        "icp_segment": perf.icp_segment,
                        "open_rate": f"{perf.open_rate:.1%}",
                        "diagnosis": "Subject line issue"
                    })
                elif perf.reply_rate < 0.01:
                    insights["underperformers"].append({
                        "issue": "Low reply rate",
                        "angle": perf.angle,
                        "icp_segment": perf.icp_segment,
                        "reply_rate": f"{perf.reply_rate:.1%}",
                        "diagnosis": "Angle or relevance issue"
                    })
        
        # Generate recommendations
        if insights["best_performers"]:
            top = insights["best_performers"][0]
            insights["iteration_recommendations"].append(
                f"Scale {top['angle']} angle for {top['icp_segment']} segment"
            )
        
        if insights["underperformers"]:
            insights["iteration_recommendations"].append(
                "Test alternative angles for underperforming segments"
            )
        
        return insights
    
    def export_for_router(self, output_path: Path):
        """Export performance data in format for DecisionRouter"""
        performances = self.get_campaign_performance()
        
        # Filter for statistically significant results (>= 20 sends)
        significant = [p for p in performances if p.total_sent >= 20]
        
        history_data = [
            {
                "angle": p.angle,
                "icp_segment": p.icp_segment,
                "open_rate": p.open_rate,
                "reply_rate": p.reply_rate,
                "conversion_rate": p.conversion_rate,
                "sample_size": p.total_sent
            }
            for p in significant
        ]
        
        with open(output_path, 'w') as f:
            json.dump(history_data, f, indent=2)
        
        print(f"Exported {len(history_data)} campaign history records to {output_path}")
