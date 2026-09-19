import os
import json
import requests
from datetime import datetime
from google.cloud import bigquery
from google.oauth2 import service_account

def main():
    print("[SENTINEL+ Node] Initializing Federal Policy & Regulation extraction...")
    
    # BigQuery Setup
    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    client = bigquery.Client(credentials=credentials, project=creds_dict['project_id'])
    
    # Dedicated flat table for SENTINEL
    table_id = f"{creds_dict['project_id']}.telemetry_bronze.sentinel_policy"
    
    # Federal Register API (No Auth Required) - Tracking new binding government rules
    url = "https://www.federalregister.gov/api/v1/documents.json?per_page=100&order=newest&conditions[type][]=RULE"
    
    timestamp_iso = datetime.utcnow().isoformat()
    bq_payload = []
    
    try:
        print("[SENTINEL] Querying US Federal Register...")
        response = requests.get(url)
        if response.status_code == 200:
            docs = response.json().get("results", [])
            
            # Filter for high-impact market and technology agencies
            target_agencies = [
                "Securities and Exchange Commission", 
                "Commerce Department", 
                "Energy Department", 
                "Treasury Department",
                "Federal Trade Commission",
                "Federal Communications Commission"
            ]
            
            for doc in docs:
                agencies = [a.get("name") for a in doc.get("agencies", [])]
                # Check if any target agency is in the document's agency list
                if any(target in agency_name for agency_name in agencies for target in target_agencies):
                    primary_agency = agencies[0] if agencies else "US_GOV"
                    
                    bq_payload.append({
                        "timestamp": timestamp_iso,
                        "domain": "SENTINEL",
                        "entity_id": primary_agency,
                        "signal_type": "Federal Regulation (RULE)",
                        "document_title": doc.get("title", "N/A"),
                        "agency": primary_agency,
                        "publication_date": doc.get("publication_date", "N/A"),
                        "document_url": doc.get("html_url", "N/A")
                    })
    except Exception as e:
        print(f"[SENTINEL ERROR] API request failed: {e}")

    if bq_payload:
        try:
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                autodetect=True, # Automatically creates the flat sentinel_policy table
            )
            job = client.load_table_from_json(bq_payload, table_id, job_config=job_config)
            job.result()  
            print(f"[SENTINEL] Successfully loaded {len(bq_payload)} regulatory actions into BigQuery.")
        except Exception as e:
            print(f"[SENTINEL ERROR] BigQuery push failed: {e}")
    else:
        print("[SENTINEL] No new high-impact regulations published today.")

if __name__ == "__main__":
    main()
    
