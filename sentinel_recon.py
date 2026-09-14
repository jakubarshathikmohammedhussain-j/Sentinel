import os
import json
import time
import urllib.parse
import xml.etree.ElementTree as ET
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------------------------
# INTELLIGENCE STREAMS & SEARCH QUERIES
# -------------------------------------------------------------------
FEEDS = {
    "Gov_Regulatory_Mandates": [
        "https://news.google.com/rss/search?q=antitrust+OR+%22EU+AI+Act%22+OR+%22FTC%22+OR+%22export+controls%22+when:2d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=%22regulatory+fine%22+OR+%22trade+sanctions%22+OR+%22tariffs%22+when:2d&hl=en-US&gl=US&ceid=US:en"
    ],
    "Corporate_Policy_Shifts": [
        "https://news.google.com/rss/search?q=%22billion+capex%22+OR+%22data+center+investment%22+OR+%22restructuring%22+when:2d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=%22merger%22+OR+%22acquisition%22+OR+%22SEC+investigation%22+when:2d&hl=en-US&gl=US&ceid=US:en"
    ]
}

COLUMNS_INTELLIGENCE = [
    "Date Logged", "Event Headline", "Primary Entity", "Jurisdiction / Scope",
    "Estimated Financial / Capex Impact", "Strategic Threat / Opportunity",
    "Consulting Advisory Mandate", "Source Link"
]

COLUMNS_CASE_STUDIES = [
    "Date Generated", "Subject Entity", "Core Event", "Complete LinkedIn Post Copy"
]

def parse_rss_feed(url):
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source = item.find("source").text if item.find("source") is not None else "Global Registry"
                items.append({"title": title, "link": link, "date": pub_date, "source": source})
    except Exception as e:
        print(f"[SENTINEL] Feed ingestion error: {e}")
    return items

def analyze_intelligence(title, category):
    title_clean = title.split(" - ")[0]
    entity = "Global Enterprise"
    
    # Entity identification heuristics
    known_entities = [
        "Google", "Alphabet", "Microsoft", "Apple", "Amazon", "Meta", "Nvidia", 
        "OpenAI", "TSMC", "ASML", "Tesla", "JPMorgan", "Goldman Sachs", "BlackRock",
        "European Commission", "FTC", "SEC", "DoJ", "TSMC", "Boeing", "Siemens"
    ]
    for ent in known_entities:
        if ent.lower() in title_clean.lower():
            entity = ent
            break

    # Financial and Strategic Heuristics
    if category == "Gov_Regulatory_Mandates":
        jurisdiction = "EU / US / Cross-Border" if any(w in title_clean.lower() for w in ["eu", "europe", "ftc", "us"]) else "Global Market"
        financial = "Regulatory Exposure / Compliance Capex ($100M - $1B+)"
        threat = "Market Access Restriction & Compliance Penalty Friction"
        mandate = "Enterprise Regulatory Redesign & AI Governance Architecture"
    else:
        jurisdiction = "Corporate Enterprise"
        financial = "Capital Reallocation / Strategic Capex ($500M - $10B+)"
        threat = "Competitive Displacement & Balance Sheet Exposure"
        mandate = "Strategic Integration Assessment & Operating Model Overhaul"

    return {
        "headline": title_clean,
        "entity": entity,
        "jurisdiction": jurisdiction,
        "financial": financial,
        "threat": threat,
        "mandate": mandate
    }

def synthesize_linkedin_case_study(intel):
    """
    Generates an executive case study strictly following the required schema:
    Quote, What, Who, How, Content, Data, Solution, Author Quote.
    """
    post = f"""“In boardroom strategy, compliance is rarely just about legal conformity—it is an economic moat in disguise.”

**WHAT:**
{intel['headline']} representing a fundamental market realignment in {intel['jurisdiction']}.

**WHO:**
Primary Stakeholders: {intel['entity']}, Enterprise Regulators, Institutional Capital Allocators, and Competing Market Ecosystems.

**HOW:**
By altering structural cost baselines through {intel['threat'].lower()}, creating an asymmetric barrier that disadvantages slower operational competitors.

**CONTENT:**
When market shifts of this scale occur, traditional management focuses on reactive damage control. This misses the strategic reality entirely. 

Whenever policy mandates or massive capital reallocations strike an industry, they permanently rewrite unit economics. Operating margins compress for legacy players that rely on manual workflows, while organizations with automated, deterministic infrastructure absorb compliance costs with zero operational latency. 

The mandate is no longer about monitoring change—it is about preemptively architecting systems that capitalize on regulatory disruption.

**DATA:**
• Estimated Impact Scale: {intel['financial']}
• Exposure Vector: {intel['threat']}
• Billable Advisory Horizon: Immediate 12–24 Month Operating Cycle

**SOLUTION:**
1. Governance Decoupling: Separate operational execution layers from compliance reporting to eliminate audit latency.
2. Capex Stress-Testing: Quantify the direct cash-flow impact of regulatory compliance vs. automated remediation pipelines.
3. Asymmetric Moat Building: Use compliance barriers to aggressively consolidate market share against under-capitalized peers.

“Strategy is the deliberate choice to be different and deterministic when the macro landscape becomes volatile.”
— Mohammed Hussain J."""

    return post

def send_sentinel_email(logged_items, featured_post, recipient_email):
    sender_email = os.environ.get('GMAIL_USER')
    sender_password = os.environ.get('GMAIL_APP_PASSWORD')
    if not sender_email or not sender_password:
        return

    msg = MIMEMultipart()
    today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
    msg['From'] = f"SENTINEL Strategic Intelligence <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = f"SENTINEL Executive Briefing: {len(logged_items)} Strategic Policy Events & Case Study ({today_str})"

    def format_card(item):
        return f"""
        <div style="border-left: 4px solid #0d47a1; background-color: #f8f9fa; padding: 12px; margin-bottom: 12px; border-radius: 4px;">
            <p style="margin: 0; font-size: 11px; color: #666; text-transform: uppercase; font-weight: bold;">{item['category']} &bull; {item['entity']}</p>
            <h4 style="margin: 4px 0 6px 0; color: #111;">{item['headline']}</h4>
            <p style="margin: 2px 0; font-size: 13px;"><b>Scope:</b> {item['jurisdiction']} | <b>Exposure:</b> {item['financial']}</p>
            <p style="margin: 2px 0; font-size: 13px; color: #0d47a1;"><b>Consulting Vector:</b> {item['mandate']}</p>
            <a href="{item['link']}" style="font-size: 12px; color: #1565c0; text-decoration: none; font-weight: bold; display: inline-block; margin-top: 4px;">View Regulatory Event &rarr;</a>
        </div>
        """

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222; line-height: 1.5; max-width: 680px;">
        <h2 style="color: #0d47a1; margin-bottom: 2px;">SENTINEL Strategic Intelligence Network</h2>
        <p style="color: #555; font-size: 13px; margin-top: 0;">Boardroom Briefing &bull; {today_str}</p>
        
        <h3 style="color: #111; border-bottom: 2px solid #eee; padding-bottom: 6px;">1. Landmark Macro Disruption Log</h3>
        {''.join([format_card(i) for i in logged_items[:6]])}
        
        <h3 style="color: #111; border-bottom: 2px solid #eee; padding-bottom: 6px; margin-top: 24px;">2. Ready-to-Publish LinkedIn Strategic Case Study</h3>
        <p style="font-size: 13px; color: #555;">Copy and post directly to LinkedIn to demonstrate strategic authority:</p>
        
        <div style="background-color: #f1f3f4; border: 1px solid #ddd; padding: 16px; border-radius: 6px; white-space: pre-wrap; font-size: 13px; font-family: monospace; color: #222;">
{featured_post}
        </div>

        <br>
        <p style="font-size: 11px; color: #888;">SENTINEL Node &bull; HOLO_EARTH Autonomous Systems</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("[SENTINEL] Executive briefing successfully emailed.")
    except Exception as e:
        print(f"[SENTINEL] Email error: {e}")

def main():
    print("[SENTINEL] Initializing Strategic Reconnaissance Pipeline...")
    today_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.environ['SPREADSHEET_ID'])

    worksheets = {}
    target_tabs = ["Gov_Regulatory_Mandates", "Corporate_Policy_Shifts", "Strategic_Case_Studies"]
    for tab in target_tabs:
        try:
            worksheets[tab] = sheet.worksheet(tab)
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title=tab, rows="1500", cols="10")
            headers = COLUMNS_CASE_STUDIES if tab == "Strategic_Case_Studies" else COLUMNS_INTELLIGENCE
            ws.append_row(headers)
            worksheets[tab] = ws
            time.sleep(1.0)

    # Collect existing URLs to avoid duplicate logging
    seen_links = set()
    for tab in ["Gov_Regulatory_Mandates", "Corporate_Policy_Shifts"]:
        try:
            seen_links.update(worksheets[tab].col_values(8))
        except Exception:
            pass

    logged_items = []
    tab_batches = {"Gov_Regulatory_Mandates": [], "Corporate_Policy_Shifts": []}

    for category, feed_urls in FEEDS.items():
        for feed in feed_urls:
            raw_entries = parse_rss_feed(feed)
            for entry in raw_entries:
                if entry['link'] in seen_links or not entry['title']:
                    continue

                analysis = analyze_intelligence(entry['title'], category)
                row_data = [
                    today_str,
                    analysis['headline'],
                    analysis['entity'],
                    analysis['jurisdiction'],
                    analysis['financial'],
                    analysis['threat'],
                    analysis['mandate'],
                    entry['link']
                ]

                tab_batches[category].append(row_data)
                seen_links.add(entry['link'])
                logged_items.append({**analysis, "category": category, "link": entry['link']})

                if len(tab_batches[category]) >= 10:
                    break

    # Commit intelligence batches
    for tab, rows in tab_batches.items():
        if rows:
            ws = worksheets[tab]
            ws.append_rows(rows, value_input_option='USER_ENTERED')
            print(f"[SENTINEL] Logged {len(rows)} events into {tab}.")
            time.sleep(1.2)

    # Synthesize Top LinkedIn Strategic Case Study
    featured_post = ""
    if logged_items:
        primary_intel = logged_items[0]
        featured_post = synthesize_linkedin_case_study(primary_intel)
        
        case_study_row = [
            today_str,
            primary_intel['entity'],
            primary_intel['headline'],
            featured_post
        ]
        worksheets["Strategic_Case_Studies"].append_row(case_study_row, value_input_option='USER_ENTERED')
        print("[SENTINEL] Strategic LinkedIn Case Study generated and recorded.")

    # Auto-resize columns across all three tabs
    for tab in target_tabs:
        try:
            ws = worksheets[tab]
            col_count = 4 if tab == "Strategic_Case_Studies" else 8
            sheet.batch_update({
                "requests": [{
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": ws.id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": col_count
                        }
                    }
                }]
            })
            time.sleep(1.0)
        except Exception as e:
            print(f"[SENTINEL] Column auto-resize note on {tab}: {e}")

    # Dispatch Email Briefing
    if logged_items and os.environ.get('GMAIL_USER'):
        send_sentinel_email(logged_items, featured_post, os.environ.get('GMAIL_USER'))

    print("[SENTINEL] Autonomous strategic cycle complete.")

if __name__ == "__main__":
    main()
      
