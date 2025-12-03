"""
Test script to run a single aggregation for AAPL and verify storage in MongoDB.
Run with: .venv\Scripts\python.exe tools\run_agg_test.py
"""
import json
from config import load_config
from mongo_client import MongoWrapper
from company_ticker_fetcher import CompanyTickerFetcher
from unified_profile_aggregator import UnifiedSECProfileAggregator

cfg = load_config().config
mongo = MongoWrapper(uri=cfg['mongodb']['uri'], database=cfg['mongodb']['db_name'])
print('MongoDB:', cfg['mongodb']['uri'], 'DB:', cfg['mongodb']['db_name'])

fetcher = CompanyTickerFetcher()
company = fetcher.get_by_ticker('AAPL')
print('Company:', company)

agg = UnifiedSECProfileAggregator(mongo)

def progress_cb(level, msg):
    print('PROGRESS:', level, msg)

opts = {
    'lookback_years': 5,
    'metrics': ['Revenues','NetIncomeLoss','Assets','Liabilities'],
    'incremental': False,
    'include_trends': True,
    'include_ml_features': True
}

result = agg.aggregate_company_profile(cik=company['cik'], company_info=company, output_collection='Fundamental_Data_Pipeline_test', options=opts, progress_callback=progress_cb)

print('\nAGGREGATION RESULT KEYS:')
if result:
    print(list(result.keys()))
else:
    print('No result')

stored = mongo.find_one('Fundamental_Data_Pipeline_test', {'cik': company['cik']})
print('\nSTORED IN DB:', bool(stored))
if stored:
    print('Stored generated_at:', stored.get('generated_at'))
    print('Available keys:', list(stored.keys()))

mongo.close()

