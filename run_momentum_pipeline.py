
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# ============================================
# FOLDER CONTAINING ALL THREE PYTHON PROGRAMS
# ============================================

BASE_FOLDER = Path(__file__).resolve().parent

# ============================================
# RUN ORDER
# ============================================

PROGRAMS = [
    (
        "STEP 1 - DOWNLOAD STOCK PRICE DATA",
        "MTF_FUTstocks_yahoo_data_downloader.py"
    ),
    (
        "STEP 2 - MOMENTUM CODE 1 (1ST & 16TH)",
        "Final_Momentum_Trading_FW_Latest_Review_TXT.py"
    ),
    (
        "STEP 3 - MOMENTUM CODE 2 (EXPIRY)",
        "Momentum_Trading_FW_Updated_Holiday_Review.py"
    ),
]

# ============================================
# OUTPUT FILES TO CHECK
# ============================================

OUTPUT_FILES = [
    "01&16_Review_Date_Wise_Active_Stocks.csv",
    "Expiry_Review_Date_Wise_Active_Stocks.csv",
]

# ============================================
# EXECUTION
# ============================================

def main():

    print("=" * 65)
    print("NC WEALTH - MOMENTUM TRADING PIPELINE")
    print("Started:", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    print("=" * 65)

    if not BASE_FOLDER.is_dir():
        print("ERROR: Base folder not found.")
        print(BASE_FOLDER)
        sys.exit(1)

    for step_name, filename in PROGRAMS:

        file_path = BASE_FOLDER / filename

        print("\n" + "=" * 65)
        print(step_name)
        print("File:", filename)
        print("=" * 65)

        if not file_path.is_file():
            print("ERROR: Python file not found:")
            print(file_path)
            sys.exit(1)

        start_time = datetime.now()

        try:
            subprocess.run(
                [sys.executable, str(file_path)],
                cwd=str(BASE_FOLDER),
                check=True
            )

        except subprocess.CalledProcessError as error:
            print("\nPIPELINE STOPPED!")
            print("Failed step:", step_name)
            print("Exit code:", error.returncode)
            sys.exit(error.returncode or 1)

        elapsed = datetime.now() - start_time

        print("\nCOMPLETED:", step_name)
        print("Time taken:", elapsed)

    print("\n" + "=" * 65)
    print("CHECKING HISTORICAL WATCHLIST FILES")
    print("=" * 65)

    missing_files = []

    for filename in OUTPUT_FILES:

        path = BASE_FOLDER / filename

        if path.is_file() and path.stat().st_size > 0:
            print("FOUND:", filename)
        else:
            print("MISSING OR EMPTY:", filename)
            missing_files.append(filename)

    if missing_files:
        print("\nWARNING: Some expected watchlist files are missing.")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("ALL THREE PROGRAMS COMPLETED")
    print("Historical watchlist files are present.")
    print("Finished:", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    print("=" * 65)


if __name__ == "__main__":
    main()
