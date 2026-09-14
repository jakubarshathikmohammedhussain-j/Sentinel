import os
import json
import time
import random
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

COLUMNS = [
    "Date Logged", "Event Headline", "Primary Entity", "Jurisdiction / Scope",
    "Estimated Financial / Capex Impact", "Strategic Threat / Opportunity",
    "Consulting Advisory Mandate", "Source Link"
]

# -------------------------------------------------------------
# REGULATORY DATA TEMPLATES (500+ Rows)
# -------------------------------------------------------------
REGULATORY_TEMPLATES = [
    {
        "entities": ["US Dept of Justice (DoJ)", "Federal Trade Commission (FTC)", "European Commission", "UK Competition & Markets Authority (CMA)"],
        "events": [
            "Initiates Phase 2 antitrust probe into cloud infrastructure market dominance",
            "Files federal suit to block proposed $4B horizontal acquisition",
            "Issues ruling invalidating default search engine distribution contracts",
            "Proposes structural separation of ad-tech and platform infrastructure"
        ],
        "scopes": ["US Federal Court", "EU Cross-Border", "UK Jurisdiction"],
        "impacts": ["Treble Damages Exposure ($1B - $5B)", "Structural Breakup Risk / Divestiture", "Operating Margin Compression (+12% Compliance Overhead)"],
        "threats": ["Ecosystem fragmentation & forced IP sharing", "Loss of proprietary data moats", "Mandatory competitor interoperability"],
        "mandates": ["Antitrust Defensive Architecture & Divestiture Prep", "Platform Interoperability Engineering", "Regulatory Spin-off Feasibility Study"]
    },
    {
        "entities": ["European AI Office", "US Commerce Dept", "SEC Regulatory Board", "GCC Economic Council"],
        "events": [
            "Enforces strict data localization and sovereignty requirements on hyperscalers",
            "Expands Tier-2 export controls on advanced semiconductor IP and tooling",
            "Mandates comprehensive Scope 3 carbon emissions audit and public disclosure",
            "Levies $450M fine for algorithmic bias and data privacy non-compliance"
        ],
        "scopes": ["Global Cross-Border", "EU / Sovereign Regions", "Middle East Free Zones"],
        "impacts": ["$200M+ Compliance / Sovereign Cloud Capex", "Market Access Restriction (Asian Corridors)", "Direct Regulatory Penalties (Up to 4% Global Turnover)"],
        "threats": ["Supply chain decoupling & revenue lock-out", "Massive overhead in localized data center builds", "Executive liability for ESG non-compliance"],
        "mandates": ["Sovereign Cloud Architecture Migration", "Geopolitical Supply Chain Decoupling", "Automated ESG & Carbon Telemetry Implementation"]
    }
]

# -------------------------------------------------------------
# CORPORATE SHIFT TEMPLATES (500+ Rows)
# -------------------------------------------------------------
CORPORATE_TEMPLATES = [
    {
        "entities": ["Alphabet / Google", "Microsoft Corp", "Amazon.com", "Meta Platforms", "Apple Inc."],
        "events": [
            "Commits to multi-billion dollar sovereign AI infrastructure build",
            "Executes strategic 12% workforce reduction targeting legacy hardware units",
            "Files SEC 8-K: Material reorganization of core engineering divisions",
            "Announces $2.5B acquisition of leading AI cybersecurity architecture firm",
            "Pivots supply chain, migrating 18% of hardware assembly to India/Vietnam"
        ],
        "scopes": ["Global Operations", "Asia-Pacific Manufacturing", "European Infrastructure"],
        "impacts": ["$2B - $5B Dedicated Capex Commitment", "$1B+ Annual Run-Rate Operating Cost Reduction", "Supply Base Diversification Capex"],
        "threats": ["Aggressive Moat Building (Compute/AI)", "Balance Sheet Optimization / Cost Diligence", "Hardware Supply Chain De-Risking"],
        "mandates": ["M&A Post-Merger Integration Strategy", "Supply Chain Nearshoring & Vendor Validation", "Large-Scale Organizational Restructuring"]
    },
    {
        "entities": ["Nvidia", "TSMC", "JPMorgan Chase", "Goldman Sachs", "BlackRock"],
        "events": [
            "Authorizes construction of next-generation 2nm fabrication facility",
            "Launches $30B joint venture fund for global energy and compute infrastructure",
            "Files SEC 8-K: Strategic exit from underperforming consumer banking portfolio",
            "Announces major joint venture to secure rare-earth mineral supply chains",
            "Initiates $10B accelerated share repurchase (buyback) program"
        ],
        "scopes": ["US / Taiwan Corridors", "Global Capital Markets", "Alternative Asset Infrastructure"],
        "impacts": ["$10B+ Strategic Infrastructure Deployment", "Capital Realignment / Liquidity Deployment", "Structural Operating Model Shift"],
        "threats": ["Monopolization of critical supply/compute bottlenecks", "Aggressive capital deployment signaling market tops", "Divestment of high-friction low-margin assets"],
        "mandates": ["Capital Allocation & ROI Strategy", "Joint-Venture Governance Architecture", "Divestiture & Asset Carve-Out Advisory"]
    }
]

def build_dataset(templates, count, start_days_ago=730):
    rows = []
    current_date = datetime.now() - timedelta(days=start_days_ago)
    day_step = start_days_ago / count

    for _ in range(count):
        log_date = current_date.strftime('%Y-%m-%d')
        template = random.choice(templates)
        
        entity = random.choice(template["entities"])
        event = random.choice(template["events"])
        scope = random.choice(template["scopes"])
        impact = random.choice(template["impacts"])
        threat = random.choice(template["threats"])
        mandate = random.choice(template["mandates"])

        # Format headlines realistically
        if "SEC 8-K" in event:
            headline = f"{entity}: {event}"
        else:
            headline = f"{entity} {event[0].lower() + event[1:]}"

        rows.append([
            log_date, headline, entity, scope, impact, threat, mandate, "https://sec.gov" if "SEC" in headline else "https://bloomberg.com/markets"
        ])
        
        current_date += timedelta(days=day_step)
        
    return rows

def main():
    print("[SENTINEL Master Backfill] Initializing connection to Google Sheets...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.environ['SPREADSHEET_ID'])

    print("[SENTINEL Master Backfill] Synthesizing 1,020 boardroom-level strategic events...")
    reg_rows = build_dataset(REGULATORY_TEMPLATES, 510)
    corp_rows = build_dataset(CORPORATE_TEMPLATES, 510)

    tabs = {
        "Gov_Regulatory_Mandates": reg_rows,
        "Corporate_Policy_Shifts": corp_rows
    }

    for tab_title, rows in tabs.items():
        try:
            ws = sheet.worksheet(tab_title)
            ws.clear()
            print(f"[SENTINEL Master Backfill] Cleared existing tab '{tab_title}'.")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title=tab_title, rows="1500", cols="8")
            print(f"[SENTINEL Master Backfill] Created new tab '{tab_title}'.")

        full_payload = [COLUMNS] + rows
        chunk_size = 250
        total_chunks = (len(full_payload) + chunk_size - 1) // chunk_size

        for idx, i in enumerate(range(0, len(full_payload), chunk_size)):
            chunk = full_payload[i:i + chunk_size]
            ws.append_rows(chunk, value_input_option='USER_ENTERED')
            print(f"[SENTINEL Master Backfill] {tab_title}: Injected batch {idx + 1}/{total_chunks}...")
            time.sleep(1.5) # Prevent API rate limits

        print(f"[SENTINEL Master Backfill] Auto-resizing columns for {tab_title}...")
        try:
            sheet.batch_update({
                "requests": [{
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": ws.id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 8
                        }
                    }
                }]
            })
            time.sleep(1.0)
        except Exception as e:
            print(f"[SENTINEL Master Backfill] Auto-resize note: {e}")

    print("[SENTINEL Master Backfill] Successfully committed 1,020 macro-strategic records!")

if __name__ == "__main__":
    main()
    
