import os
import json
import time
import requests
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.oauth2 import service_account

def main():
    print("[SENTINEL] Initializing 10-Year Federal Register Backfill...")

    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    client = bigquery.Client(credentials=credentials, project=creds_dict['project_id'])
    table_id = f"{creds_dict['project_id']}.telemetry_bronze.sentinel_policy"

    # Match existing schema in BigQuery
    headers = {
        "User-Agent": "HoloEarthPolicyResearch ResearchOps@holoearth.internal",
        "Accept": "application/json"
    }

    start_date = (datetime.utcnow() - timedelta(days=10*365)).strftime('%Y-%m-%d')
    timestamp_iso = datetime.utcnow().isoformat()

    # High-impact federal regulatory agencies
    target_agencies = [
        "defense-department",
        "energy-department",
        "commerce-department",
        "environmental-protection-agency",
        "transportation-department",
        "treasury-department",
        "federal-communications-commission"
    ]

    all_records = []
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        ignore_unknown_values=True
    )

    for agency in target_agencies:
        print(f"[SENTINEL] Pulling 10-year regulations for {agency}...")
        page = 1
        has_more = True

        while has_more and page <= 50:  # Pull up to 5,000 top rules per agency
            url = (
                f"https://www.federalregister.gov/api/v1/documents.json"
                f"?conditions[agency_slugs][]={agency}"
                f"&conditions[publication_date][gte]={start_date}"
                f"&conditions[type][]=RULE"
                f"&per_page=100"
                f"&page={page}"
            )

            try:
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if not results:
                        break

                    for rule in results:
                        # Matches your exact existing column structure
                        all_records.append({
                            "timestamp": timestamp_iso,
                            "publication_date": rule.get("publication_date", ""),
                            "agency": agency.replace("-", " ").title(),
                            "document_title": str(rule.get("title", ""))[:250],
                            "signal_type": "FINAL_RULE"
                        })

                    # Flush batch when size exceeds 3,000 records
                    if len(all_records) >= 3000:
                        client.load_table_from_json(all_records, table_id, job_config=job_config).result()
                        print(f"[SENTINEL] Loaded {len(all_records)} records into {table_id}.")
                        all_records = []

                    total_pages = data.get("total_pages", 1)
                    if page < total_pages:
                        page += 1
                        time.sleep(0.2)
                    else:
                        has_more = False
                elif resp.status_code == 429:
                    time.sleep(5)
                else:
                    print(f"[SENTINEL ERROR] HTTP {resp.status_code} for {agency} page {page}")
                    break
            except Exception as e:
                print(f"[SENTINEL ERROR] Exception on {agency}: {e}")
                break

    if all_records:
        client.load_table_from_json(all_records, table_id, job_config=job_config).result()
        print(f"[SENTINEL] Loaded final batch of {len(all_records)} records.")

    print("[SENTINEL] Ingestion complete.")

if __name__ == "__main__":
    main()
    
