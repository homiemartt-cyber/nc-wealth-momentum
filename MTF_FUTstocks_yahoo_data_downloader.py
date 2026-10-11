"""Download daily Yahoo Finance candles for the futures universe.
Full history is refreshed each run; no GitHub runner persistence is required.
"""
from pathlib import Path
import os
import time
import pandas as pd
import yfinance as yf

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / 'Futures Stock List.csv'
DATA_DIR = BASE_DIR / 'MTF_FUTstocks_data' / 'daily'
START_DATE = '2025-01-01'
MIN_SUCCESS_RATIO = 0.95
DATA_DIR.mkdir(parents=True, exist_ok=True)

universe = pd.read_csv(INPUT_FILE)
col = next((c for c in universe.columns if c.strip().lower() in ('symbol','symbols','ticker')), None)
if col is None:
    raise RuntimeError('Symbol column not found in Futures Stock List.csv')
symbols = list(dict.fromkeys(str(s).strip() for s in universe[col].dropna() if str(s).strip()))
if '^CRSLDX' not in symbols:
    symbols.append('^CRSLDX')

success = []
failures = []
for i, sym in enumerate(symbols, 1):
    ticker = sym if sym.startswith('^') or sym.endswith(('.NS','.BO')) else sym + '.NS'
    for attempt in range(1, 4):
        try:
            df = yf.download(ticker, start=START_DATE, interval='1d', progress=False,
                             auto_adjust=False, threads=False, timeout=30)
            if df.empty:
                raise ValueError('empty Yahoo Finance response')
            df = df.reset_index()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [str(c).strip() for c in df.columns]
            if not {'Date','Open','Close'}.issubset(df.columns):
                raise ValueError('missing Date/Open/Close columns')
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.tz_localize(None)
            df = df.dropna(subset=['Date','Open','Close']).sort_values('Date')
            if len(df) < 55:
                raise ValueError(f'insufficient price history: {len(df)} sessions')
            target = DATA_DIR / f'{sym}.csv'
            temp = target.with_suffix('.csv.tmp')
            df.to_csv(temp, index=False)
            os.replace(temp, target)
            success.append(sym)
            print(f'[{i}/{len(symbols)}] OK {sym}: latest {df.Date.iloc[-1].date()}', flush=True)
            break
        except Exception as exc:
            if attempt == 3:
                failures.append((sym,str(exc)))
                print(f'[{i}/{len(symbols)}] FAILED {sym}: {exc}', flush=True)
            else:
                time.sleep(3 * attempt)

print(f'Downloaded {len(success)}/{len(symbols)} symbols. Failures: {failures}', flush=True)
if '^CRSLDX' not in success:
    raise RuntimeError('Critical index ^CRSLDX failed to download; aborting publication')
if len(success) / len(symbols) < MIN_SUCCESS_RATIO:
    raise RuntimeError(f'Download coverage below {MIN_SUCCESS_RATIO:.0%}; aborting publication')

# A market holiday is allowed to retain the previous session's data.
# The website should show the actual data date rather than imply a fresh trading session.
