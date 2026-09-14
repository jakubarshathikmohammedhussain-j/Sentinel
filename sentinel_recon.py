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
import yfinance as yf
import ta

FEEDS = {
    "Gov_Regulatory_Mandates": [
        "https://news.google.com/rss/search?q=antitrust+OR+%22EU+AI+Act%22+OR+%22FTC%22+OR+%22export+controls%22+when:2d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=%22regulatory+fine%22+OR+%22trade+sanctions%22+OR+%22tariffs%22+when:2d&hl=en-US&gl=US&ceid=US:en"
    ],
    "Corporate_Policy_Shifts": [
        "https://news.google.com/rss/search?q=%22billion+capex%22+OR+%22data+center+investment%22+OR+%22restructuring%22+when:2d&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=%22merger%22+OR+%22acquisition%22+OR+%22SEC+filing%22+when:2d&hl=en-US&gl=US&ceid=US:en"
    ]
}

COLUMNS_INTELLIGENCE = [
    "Date Logged", "Event Headline", "Primary Entity", "Jurisdiction / Scope",
    "Estimated Financial / Capex Impact", "Strategic Threat / Opportunity",
    "Consulting Advisory Mandate", "Source Link"
]

TICKER_MAP = {
    "google": "GOOGL", "alphabet": "GOOGL", "microsoft": "MSFT", "apple": "AAPL",
    "nvidia": "NVDA", "amazon": "AMZN", "meta": "META", "tsmc": "TSM",
    "jpmorgan": "JPM", "goldman": "GS", "fedex": "FDX", "ups": "UPS"
}

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
                items.append({"title": title, "link": link})
    except Exception as e:
        print(f"[SENTINEL] Feed error: {e}")
    return items

def get_rich_market_correlation(entity_name):
    """RICH Engine Bridge: Fetches live RSI, P/E, and Volume for the affected entity."""
    matched_ticker = None
    for k, v in TICKER_MAP.items():
        if k in entity_name.lower():
            matched_ticker = v
            break
            
    if not matched_ticker:
        return None

    try:
        tk = yf.Ticker(matched_ticker)
        hist = tk.history(period="1mo")
        if len(hist) >= 14:
            rsi_series = ta.momentum.RSIIndicator(hist['Close'], window=14).rsi()
            current_rsi = round(rsi_series.iloc[-1], 2)
            current_close = round(hist['Close'].iloc[-1], 2)
            vol = int(hist['Volume'].iloc[-1])
            avg_vol = int(hist['Volume'].mean())
            vol_shock = round(vol / avg_vol, 2)
            pe = round(tk.info.get('forwardPE', 0), 2)
            return {
                "ticker": matched_ticker,
                "price": current_close,
                "rsi": current_rsi,
                "volume_shock": vol_shock,
                "forward_pe": pe
            }
    except Exception as e:
        print(f"[SENTINEL] RICH Bridge query error: {e}")
    return None

def analyze_event(title, category):
    title_clean = title.split(" - ")[0]
    entity = "Global Enterprise"
    
    for k in TICKER_MAP.keys():
        if k in title_clean.lower():
            entity = k.title()
            break

    if category == "Gov_Regulatory_Mandates":
        jurisdiction = "EU / US Regulatory Desks"
        financial = "Regulatory Fine Exposure / Compliance Capex ($150M - $1.5B)"
        threat = "Market Access Restriction & Monopolistic Channel De-linking"
        mandate = "Enterprise Governance Decoupling & Compliance Automation"
    else:
        jurisdiction = "Corporate Infrastructure"
        financial = "Capital Realignment / Direct Capex ($500M - $10B+)"
        threat = "Operating Margin Compression & Structural Depreciation"
        mandate = "M&A Integration & Operating Model Transformation"

    return {
        "headline": title_clean,
        "entity": entity,
        "jurisdiction": jurisdiction,
        "financial": financial,
        "threat": threat,
        "mandate": mandate
    }

def generate_linkedin_case_study(intel, market_data):
    """Synthesizes the story-based case study using real data."""
    market_str = ""
    if market_data:
        market_str = f"• RICH Equity Telemetry: {market_data['ticker']} @ ${market_data['price']} | 14-Day RSI: {market_data['rsi']} | Volume Shock: {market_data['volume_shock']}x vs 30D Avg | Fwd P/E: {market_data['forward_pe']}\n"

    post = f"""“In boardroom strategy, compliance is rarely just about legal conformity—it is an economic moat in disguise.”

**WHAT:**
{intel['headline']} representing a fundamental market realignment in {intel['jurisdiction']}.

**WHO:**
Primary Stakeholders: {intel['entity']}, Enterprise Regulators, Institutional Capital Allocators, and Ecosystem Competitors.

**HOW:**
By fundamentally altering operational cost baselines through {intel['threat'].lower()}, creating an asymmetric barrier that disadvantages slower operational competitors.

**CONTENT:**
When market shifts of this magnitude occur, executive committees often default to reactive damage control. This misses the strategic reality entirely. 

Whenever policy mandates or massive capital reallocations strike an industry, they permanently rewrite unit economics. Operating margins compress for legacy players that rely on manual workflows, while organizations with automated, deterministic infrastructure absorb compliance costs with zero operational latency. 

The mandate is no longer about monitoring change—it is about preemptively architecting systems that capitalize on regulatory disruption.

**DATA:**
• Estimated Impact Scale: {intel['financial']}
• Exposure Vector: {intel['threat']}
{market_str}• Advisory Horizon: Immediate 12–24 Month Operating Cycle

**SOLUTION:**
1. Governance Decoupling: Separate operational execution layers from compliance reporting to eliminate audit latency.
2. Capex Stress-Testing: Quantify the direct cash-flow impact of regulatory compliance vs. automated remediation pipelines.
3. Asymmetric Moat Building: Use compliance barriers to aggressively consolidate market share against under-capitalized peers.

“Strategy is the deliberate choice to be different and deterministic when the macro landscape becomes volatile.”
— Mohammed Hussain J."""
    return post

def generate_mece_case_interview(intel):
    """Generates a partner-level MECE consulting case interview simulation."""
    return f"""**Boardroom Case Prompt:**
The CEO of a Fortune 500 company in the {intel['entity']} ecosystem asks your consulting team: 
*'Given that "{intel['headline']}" has altered our operational baseline, should we absorb compliance costs, divest impacted business units, or restructure our core platform?'*

**MECE Solution Framework (3 Pillars):**
1. **Pillar 1: Revenue & Market Defense (Commercial Vector)**
   • Quantify total addressable market (TAM) exposed to new restrictions.
   • Evaluate pricing elasticity if compliance overhead is passed to end-clients.
2. **Pillar 2: Cost & Infrastructure Resilience (Operational Vector)**
   • Audit current compliance run-rate spend against automated telemetry alternatives.
   • Determine whether to build internal governance architectures or outsource to specialized enterprise partners.
3. **Pillar 3: Strategic Optionality & M&A (Corporate Finance Vector)**
   • Stress-test balance sheet resilience under worst-case regulatory penalties.
   • Identify vulnerable competitors ripe for distressed acquisition."""

def send_whatsapp_alert(post_text):
    """Dispatches the post directly to WhatsApp using CallMeBot API if configured."""
    phone = os.environ.get('WHATSAPP_PHONE')
    apikey = os.environ.get('WHATSAPP_API_KEY')
    if not phone or not apikey:
        return

    # Shorten for WhatsApp transmission limit
    wa_message = f"*SENTINEL LinkedIn Post Ready:*\n\n{post_text[:1200]}...\n\n_(Full version delivered to your Gmail inbox)_"
    encoded_text = urllib.parse.quote(wa_message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_text}&apikey={apikey}"
    try:
        requests.get(url, timeout=10)
        print("[SENTINEL] WhatsApp alert dispatched.")
    except Exception as e:
        print(f"[SENTINEL] WhatsApp error: {e}")

def send_email_briefing(logged_items, post_copy, mece_case, recipient_email):
    sender_email = os.environ.get('GMAIL_USER')
    sender_password = os.environ.get('GMAIL_APP_PASSWORD')
    if not sender_email or not sender_password:
        return

    msg = MIMEMultipart()
    today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
    msg['From'] = f"SENTINEL Central Command <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = f"SENTINEL Executive Briefing: {today_str} Strategic Policy & Boardroom Case"

    def format_card(i):
        return f"""
        <div style="border-left: 4px solid #0d47a1; background-color: #f8f9fa; padding: 12px; margin-bottom: 12px; border-radius: 4px;">
            <p style="margin: 0; font-size: 11px; color: #666; text-transform: uppercase; font-weight: bold;">{i['entity']} &bull; {i['jurisdiction']}</p>
            <h4 style="margin: 4px 0 6px 0; color: #111;">{i['headline']}</h4>
            <p style="margin: 2px 0; font-size: 13px;"><b>Exposure:</b> {i['financial']}</p>
            <p style="margin: 2px 0; font-size: 13px; color: #0d47a1;"><b>Consulting Vector:</b> {i['mandate']}</p>
        </div>
        """

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222; line-height: 1.5; max-width: 680px;">
        <h2 style="color: #0d47a1; margin-bottom: 2px;">SENTINEL Strategic Intelligence Network</h2>
        <p style="color: #666; font-size: 13px; margin-top: 0;">Boardroom Intelligence &bull; {today_str}</p>
        
        <h3 style="color: #111; border-bottom: 2px solid #eee; padding-bottom: 6px;">1. High-Impact Policy & Capex Shifts</h3>
        {''.join([format_card(i) for i in logged_items[:5]])}
        
        <h3 style="color: #111; border-bottom: 2px solid #eee; padding-bottom: 6px; margin-top: 24px;">2. Ready-to-Publish LinkedIn Strategic Case Study</h3>
        <p style="font-size: 13px; color: #555;">Copy and paste directly to LinkedIn:</p>
        <div style="background-color: #f1f3f4; border: 1px solid #ddd; padding: 16px; border-radius: 6px; white-space: pre-wrap; font-size: 13px; font-family: monospace; color: #111;">
{post_copy}
        </div>

        <h3 style="color: #111; border-bottom: 2px solid #eee; padding-bottom: 6px; margin-top: 24px;">3. Boardroom MECE Case Interview Simulation</h3>
        <div style="background-color: #e8f0fe; border-left: 4px solid #1967d2; padding: 14px; border-radius: 4px; font-size: 13px; color: #111; white-space: pre-wrap;">
{mece_case}
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
        print("[SENTINEL] Executive briefing emailed.")
    except Exception as e:
        print(f"[SENTINEL] Email error: {e}")

def main():
    print("[SENTINEL Master] Ingesting real-time policy and corporate shifts...")
    today_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.environ['SPREADSHEET_ID'])

    worksheets = {}
    target_tabs = ["Gov_Regulatory_Mandates", "Corporate_Policy_Shifts"]
    for tab in target_tabs:
        try:
            worksheets[tab] = sheet.worksheet(tab)
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title=tab, rows="2000", cols="8")
            ws.append_row(COLUMNS_INTELLIGENCE)
            worksheets[tab] = ws
            time.sleep(1)

    seen_links = set()
    for tab in target_tabs:
        try:
            seen_links.update(worksheets[tab].col_values(8))
        except Exception:
            pass

    logged_items = []
    tab_batches = {"Gov_Regulatory_Mandates": [], "Corporate_Policy_Shifts": []}

    for category, feeds in FEEDS.items():
        for f in feeds:
            entries = parse_rss_feed(f)
            for entry in entries:
                if entry['link'] in seen_links or not entry['title']:
                    continue

                analysis = analyze_event(entry['title'], category)
                row_data = [
                    today_str, analysis['headline'], analysis['entity'], analysis['jurisdiction'],
                    analysis['financial'], analysis['threat'], analysis['mandate'], entry['link']
                ]

                tab_batches[category].append(row_data)
                seen_links.add(entry['link'])
                logged_items.append({**analysis, "link": entry['link'], "category": category})

                if len(tab_batches[category]) >= 10:
                    break

    # Commit structured intelligence to Sheets
    for tab, rows in tab_batches.items():
        if rows:
            ws = worksheets[tab]
            ws.append_rows(rows, value_input_option='USER_ENTERED')
            print(f"[SENTINEL] Logged {len(rows)} events into '{tab}'.")

    # Auto-resize columns
    for tab in target_tabs:
        try:
            ws = worksheets[tab]
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
            time.sleep(1)
        except Exception as e:
            print(f"[SENTINEL] Auto-resize note: {e}")

    # Generate Case Study & MECE Framework
    if logged_items:
        lead_event = logged_items[0]
        # Query RICH bridge
        market_data = get_rich_market_correlation(lead_event['entity'])
        
        post_copy = generate_linkedin_case_study(lead_event, market_data)
        mece_case = generate_mece_case_interview(lead_event)
        
        # Dispatch Multi-Channel Briefings
        send_email_briefing(logged_items, post_copy, mece_case, os.environ.get('GMAIL_USER'))
        send_whatsapp_alert(post_copy)

    print("[SENTINEL Master] Daily execution complete.")

if __name__ == "__main__":
    main()
    
