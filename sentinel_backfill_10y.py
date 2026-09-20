import os
import json
import time
import requests
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.oauth2 import service_account

def main():
    print("[SENTINEL BACKFILL] Initializing 10-Year Federal Register Pipeline...")
    
    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    client = bigquery.Client(credentials=credentials, project=creds_dict['project_id'])
    table_id = f"{creds_dict['project_id']}.telemetry_bronze.sentinel_policy"

    start_date = (datetime.utcnow() - timedelta(days=10*365)).strftime('%Y-%m-%d')
    timestamp_iso = datetime.utcnow().isoformat()
    
    target_agencies = [
        "defense-department", 
        "energy-department", 
        "commerce-department", 
        "environmental-protection-agency", 
        "transportation-department", 
        "treasury-department", 
        "homeland-security-department"
    ]
    
    all_rules = []
    chunk_size = 5000

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        ignore_unknown_values=True,
        autodetect=True
    )
    
    for agency in target_agencies:
        print(f"[SENTINEL] Fetching 10-year regulatory history for {agency}...")
        page = 1
        has_more = True
        
        while has_more:
            url = (
                f"https://www.federalregister.gov/api/v1/documents.json"
                f"?conditions[agency_slugs][]={agency}"
                f"&conditions[publication_date][gte]={start_date}"
                f"&conditions[type][]=RULE"
                f"&conditions[type][]=PRORULE"
                f"&per_page=1000"
                f"&page={page}"
            )
            
            try:
                response = requests.get(url, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    if not results:
                        break
                        
                    for rule in results:
                        all_rules.append({
                            "timestamp": timestamp_iso,
                            "domain": "SENTINEL",
                            "entity_id": agency.upper().replace("-", "_"),
                            "signal_type": rule.get("type", "UNKNOWN"),
                            "policy_title": str(rule.get("title", ""))[:250],
                            "publication_date": rule.get("publication_date", ""),
                            "document_number": str(rule.get("document_number", "N/A")),
                            "pdf_url": str(rule.get("pdf_url", "")),
                            "action": str(rule.get("action", "N/A"))[:200]
                        })
                    
                    if len(all_rules) >= chunk_size:
                        client.load_table_from_json(all_rules, table_id, job_config=job_config).result()
                        print(f"[SENTINEL] Committed batch of {len(all_rules)} rows to BigQuery.")
                        all_rules = []

                    total_pages = data.get("total_pages", 1)
                    if page < total_pages:
                        page += 1
                        time.sleep(0.3)
                    else:
                        has_more = False
                else:
                    print(f"[SENTINEL ERROR] HTTP {response.status_code} for {agency} page {page}")
                    break
            except Exception as e:
                print(f"[SENTINEL ERROR] Failed on {agency}: {e}")
                break

    if all_rules:
        client.load_table_from_json(all_rules, table_id, job_config=job_config).result()
        print(f"[SENTINEL] Committed final batch of {len(all_rules)} rows.")

    print("[SENTINEL] Ingestion workflow complete.")

if __name__ == "__main__":
    main()
  
