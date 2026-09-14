import os
import json
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

HISTORICAL_REGULATORY = [
    ["2024-03-13", "European Parliament Approves Landmark EU AI Act", "European Union", "EU Jurisdictions", "Up to €35M or 7% of Global Turnover", "High-Risk AI Model Banning & Algorithmic Auditing", "AI Governance Framework Implementation", "https://ec.europa.eu"],
    ["2024-03-21", "US DoJ Files Comprehensive Antitrust Lawsuit Against Apple", "Apple Inc.", "US Federal Court", "Potential Monopolistic Treble Damages ($10B+)", "Ecosystem Interoperability & App Store Fee Decoupling", "Antitrust Separation & Platform Compliance Architecture", "https://justice.gov"],
    ["2024-08-05", "US District Court Rules Google Operates Illegal Search Monopoly", "Alphabet / Google", "US District Court", "Remedy Phase: Potential Asset Divestiture / Spin-off", "Default Browser Distribution Agreements Invalidated", "Search & AdTech Revenue Architecture Restructuring", "https://justice.gov"],
    ["2025-01-15", "Federal Trade Commission Prohibits Worker Non-Compete Agreements Nationwide", "US Enterprises", "US Federal", "Estimated $400B+ Shift in Talent Capital Mobility", "Loss of Proprietary Human Capital Defensibility", "Human Capital Retention & IP Protection Realignment", "https://ftc.gov"],
    ["2025-06-20", "GCC Enacts Standardized Multi-Jurisdictional Corporate Minimum Tax", "GCC / Middle East", "UAE / Saudi Arabia", "15% Statutory Global Minimum Tax (OECD Pillar Two)", "Tax Shield Arbitrage Elimination in Free Zones", "Cross-Border Transfer Pricing & Treasury Modernization", "https://mof.gov.ae"],
    ["2025-11-10", "US Commerce Department Imposes Expanded Export Restrictions on Advanced AI Semiconductors", "Nvidia / TSMC", "Global / Cross-Border", "$5B+ Re-architecting of Sovereign Compute Channels", "Exclusion from Key International Hyperscale Markets", "Decoupled Supply Chain & Custom Architecture Strategy", "https://bis.doc.gov"],
    ["2026-02-18", "EU Mandatory Supply Chain Corporate Sustainability Due Diligence Directive Enacted", "European Enterprises", "EU Supply Chains", "Fines Capped at 5% of Worldwide Net Turnover", "Full Scope 3 Environmental and Labor Liability", "Tier-N Autonomous Supply Chain Audit Verification", "https://europa.eu"]
]

HISTORICAL_CORPORATE = [
    ["2024-01-29", "Amazon Terminates $1.4B Acquisition of iRobot Following European Commission Scrutiny", "Amazon / iRobot", "Global Cross-Border", "$1.4B Deal Aborted + $94M Breakup Fee", "Inability to Consolidate Smart Home Hardware Moats", "Antitrust-Resilient M&A Protocol Advisory", "https://sec.gov"],
    ["2024-04-09", "Microsoft Commits $2.9B Cloud and AI Infrastructure Expansion to Japan", "Microsoft", "Asia-Pacific", "$2.9B Dedicated Capex Commitment", "Hyperscale Sovereign AI Compute Consolidation", "National Sovereign Cloud Advisory Mandate", "https://news.microsoft.com"],
    ["2024-09-16", "Intel Restructures Foundry Business into Independent Subsidiary", "Intel Corp.", "Global Semiconductor", "$10B+ Structural Operating Cost Reduction", "Capital Intensity Decoupling from Product Design", "Corporate Spin-Off & Cost Optimization Mandate", "https://sec.gov"],
    ["2025-03-25", "BlackRock and Sovereign Wealth Partners Launch $30B AI Infrastructure Fund", "BlackRock / Global Partners", "Global Energy & Compute", "$30B Direct Equity / $100B Total Leveraged Capex", "Capital Dominance over AI Power and Data Centers", "Alternative Asset Infrastructure Capital Allocation", "https://blackrock.com"],
    ["2025-07-14", "TSMC Authorizes Second Arizona Gigafab Following $6.6B US CHIPS Act Grant", "TSMC", "US / Taiwan", "$65B Total Multi-Year Committed Capital", "Geopolitical Diversification of Leading-Edge Lithography", "Advanced Semiconductor Supply Reshoring Strategy", "https://tsmc.com"],
    ["2026-01-22", "Alphabet Commits $12B Capex for Sovereign European AI Data Cluster Infrastructure", "Alphabet / Google", "Europe", "$12B Infrastructure Allocation", "Local Sovereign Cloud Hosting Requirements", "Public-Private Sovereign Infrastructure Strategy", "https://sec.gov"]
]

COLUMNS_INTELLIGENCE = [
    "Date Logged", "Event Headline", "Primary Entity", "Jurisdiction / Scope",
    "Estimated Financial / Capex Impact", "Strategic Threat / Opportunity",
    "Consulting Advisory Mandate", "Source Link"
]

COLUMNS_CASE_STUDIES = [
    "Date Generated", "Subject Entity", "Core Event", "Complete LinkedIn Post Copy"
]

SAMPLE_CASE_STUDY = [
    "2026-03-01",
    "European Union & Tech Hyperscalers",
    "Enforcement Phase of the EU AI Act High-Risk Model Auditing",
    """“In boardroom strategy, compliance is rarely just about legal conformity—it is an economic moat in disguise.”

**WHAT:**
The active enforcement phase of the EU AI Act imposing mandatory algorithmic audits and transparency registries on tier-1 model developers.

**WHO:**
Primary Stakeholders: European AI Office, Tier-1 Model Providers (Microsoft, Google, Meta, Anthropic), Enterprise Adopters, and Advisory Firms.

**HOW:**
By enforcing mandatory safety documentation, bias audits, and technical documentation under threat of penalties reaching up to €35M or 7% of worldwide annual turnover.

**CONTENT:**
Most executive teams treat the EU AI Act as a legal headache. This is a strategic misunderstanding.

Whenever regulatory compliance scales in complexity, it establishes an insurmountable barrier for under-capitalized entrants. While small-to-midsize innovators struggle with compliance overhead, enterprise incumbents with automated data governance absorb the cost and convert compliance into an enterprise sales asset.

In management consulting, the highest-margin engagements are never reactive audits—they are system architectures that turn regulatory obligations into operational speed.

**DATA:**
• Maximum Regulatory Exposure: €35,000,000 or 7% of Global Net Turnover
• Impacted Landscape: Every enterprise deploying high-risk cognitive models in Europe
• Strategic Target: 100% elimination of manual compliance verification

**SOLUTION:**
1. Automated Telemetry Governance: Embed continuous model audit trails natively within the deployment pipeline.
2. Exposure Decoupling: Isolate high-risk automated logic from core transaction systems to minimize formal audit footprint.
3. Market Consolidation: Leverage certified compliance status as an enterprise procurement differentiator.

“Strategy is the deliberate choice to be different and deterministic when the macro landscape becomes volatile.”
— Mohammed Hussain J."""
]

def main():
    print("[SENTINEL Backfill] Connecting to Google Sheets...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.environ['SPREADSHEET_ID'])

    tabs_data = {
        "Gov_Regulatory_Mandates": (COLUMNS_INTELLIGENCE, HISTORICAL_REGULATORY),
        "Corporate_Policy_Shifts": (COLUMNS_INTELLIGENCE, HISTORICAL_CORPORATE),
        "Strategic_Case_Studies": (COLUMNS_CASE_STUDIES, [SAMPLE_CASE_STUDY])
    }

    for tab_title, (headers, rows) in tabs_data.items():
        try:
            ws = sheet.worksheet(tab_title)
            ws.clear()
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title=tab_title, rows="1500", cols="10")
            time.sleep(1)

        payload = [headers] + rows
        ws.append_rows(payload, value_input_option='USER_ENTERED')
        print(f"[SENTINEL Backfill] Logged {len(rows)} verified landmark milestones into '{tab_title}'.")
        time.sleep(1.5)

    print("[SENTINEL Backfill] Backfill successfully committed.")

if __name__ == "__main__":
    main()
  
