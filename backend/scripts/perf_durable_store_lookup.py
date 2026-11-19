#!/usr/bin/env python3
"""Local-only synthetic benchmark for durable GEO result lookup."""
import argparse
import json
import math
import statistics
import time

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.integration.durable_outreach import DurableStore, metadata, record_table


def percentile(values, fraction):
    ordered=sorted(values)
    return ordered[max(0,math.ceil(fraction*len(ordered))-1)]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--records',type=int,default=100000)
    parser.add_argument('--samples',type=int,default=30)
    args=parser.parse_args()
    engine=create_engine('sqlite://')
    metadata.create_all(engine)
    target_profile='profile-000042'
    rows=[]
    for index in range(args.records):
        profile=f'profile-{index//10:06d}'
        version=f'inv-{index%10:02d}'
        record={'record_id':f'research-result:{profile}:{version}','source_profile_id':profile,
            'source_profile_version':version,'exported_at':f'2026-01-01T00:{index%60:02d}:00Z'}
        rows.append({'id':record['record_id'],'kind':'research_result_export','profile_id':profile,
            'profile_version':version,'payload':json.dumps(record,separators=(',',':'))})
    with engine.begin() as connection:
        for start in range(0,len(rows),1000):
            connection.execute(record_table.insert(),rows[start:start+1000])
    with Session(engine) as db:
        store=DurableStore(db)
        baseline=[];optimized=[]
        for _ in range(args.samples):
            start=time.perf_counter()
            all_rows=store.records('research_result_export')
            next((row for row in all_rows if row.get('source_profile_id')==target_profile
                  and row.get('source_profile_version')=='inv-02'),None)
            baseline.append((time.perf_counter()-start)*1000)
            start=time.perf_counter()
            store.records_for_profile('research_result_export',target_profile,'inv-02')
            optimized.append((time.perf_counter()-start)*1000)
    print(json.dumps({'synthetic_records':args.records,'samples':args.samples,
        'legacy_rows_materialized_per_lookup':args.records,
        'scoped_rows_materialized_per_lookup':1,
        'legacy_median_ms':round(statistics.median(baseline),2),
        'legacy_p95_ms':round(percentile(baseline,.95),2),
        'scoped_median_ms':round(statistics.median(optimized),2),
        'scoped_p95_ms':round(percentile(optimized,.95),2),
        'provider_calls':0,'live_data_used':False},indent=2))
    engine.dispose()


if __name__=='__main__':
    main()
