import pandas as pd
import yfinance as yf
import os
from tqdm import tqdm

# -----------------------
# CONFIG
# -----------------------
INPUT_FILE = r"C:\Users\DELL\Desktop\Automation\Momemtum Trading FW\Futures Stock List.csv"
BASE_FOLDER = r"C:\Users\DELL\Desktop\Automation\Momemtum Trading FW\MTF_FUTstocks_data"

TIMEFRAMES = {
    "1d": "daily",
    "1wk": "weekly",
    "1mo": "monthly"
}

START_DATE = "2025-01-01"

# -----------------------
# LOAD SYMBOLS
# -----------------------
df = pd.read_csv(INPUT_FILE)
df.columns = df.columns.str.strip()

symbol_col = None
for col in df.columns:
    if col.lower() in ['symbol', 'symbols', 'ticker']:
        symbol_col = col
        break

if symbol_col is None:
    raise Exception("❌ Symbol column not found")

symbols = df[symbol_col].dropna().unique().tolist()

print(f"✅ Total symbols: {len(symbols)}")

# -----------------------
# CREATE FOLDERS
# -----------------------
for folder in TIMEFRAMES.values():
    os.makedirs(os.path.join(BASE_FOLDER, folder), exist_ok=True)

# -----------------------
# SYMBOL FORMAT FUNCTION
# -----------------------
def format_symbol(sym):
    sym = sym.strip()

    # If already index (starts with ^), return as-is
    if sym.startswith("^"):
        return sym

    # Otherwise stock → add .NS
    return sym + ".NS"

# -----------------------
# DOWNLOAD LOOP
# -----------------------
for tf, folder in TIMEFRAMES.items():

    print(f"\n📥 Downloading {folder} data...")

    for sym in tqdm(symbols):

        yf_symbol = format_symbol(sym)

        try:
            data = yf.download(
                yf_symbol,
                start=START_DATE,
                interval=tf,
                progress=False
            )

            if data.empty:
                print(f"⚠️ No data for {sym}")
                continue

            data = data.reset_index()

            # Fix MultiIndex
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] for col in data.columns]

            data.columns = [str(col).strip() for col in data.columns]

            file_path = os.path.join(BASE_FOLDER, folder, f"{sym}.csv")
            data.to_csv(file_path, index=False)

        except Exception as e:
            print(f"❌ Error with {sym}: {e}")

print("✅ Multi-timeframe data download complete")