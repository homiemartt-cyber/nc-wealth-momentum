"""Upload validated output CSVs to a private Supabase Storage bucket."""
import os
from pathlib import Path
import pandas as pd
from supabase import create_client

ROOT = Path(__file__).resolve().parent
BUCKET = 'momentum-trading'
SNAPSHOTS = [
    '01&16_Review_Date_Wise_Active_Stocks.csv',
    'Expiry_Review_Date_Wise_Active_Stocks.csv',
]

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
client = create_client(url, key)

# Validate all files BEFORE publishing any.
for name in SNAPSHOTS:
    path = ROOT / name
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f'Missing/empty watchlist: {name}')
    frame = pd.read_csv(path)
    required = {'Review_Date','Data_Date','Theme','Stock'}
    if not required.issubset(frame.columns):
        raise RuntimeError(f'Invalid columns in {name}: {list(frame.columns)}')
    if frame.empty:
        raise RuntimeError(f'No historical snapshots in {name}')

price_files = sorted((ROOT / 'MTF_FUTstocks_data' / 'daily').glob('*.csv'))
if not price_files:
    raise RuntimeError('No daily price files available to publish')

for file in price_files:
    remote = f'daily-price-data/{file.name}'
    client.storage.from_(BUCKET).upload(remote, file.read_bytes(),
        {'content-type':'text/csv', 'upsert':'true'})
    print('Uploaded', remote, flush=True)

# Publish watchlists only after price files upload successfully.
for name in SNAPSHOTS:
    remote = f'historical-watchlists/{name}'
    client.storage.from_(BUCKET).upload(remote, (ROOT/name).read_bytes(),
        {'content-type':'text/csv', 'upsert':'true'})
    print('Published', remote, flush=True)
print('Supabase publication complete', flush=True)
