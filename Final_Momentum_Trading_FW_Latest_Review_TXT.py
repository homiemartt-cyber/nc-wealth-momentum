import os
from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# STRATEGY KEY POINTS
# ============================================================

# Uses 25-session and 50-session momentum returns.
# Reviews stocks on the 1st and 16th of every month.
# Ranks stocks separately for Bullish and Bearish momentum.
# Compares stock performance against the CRSLDX index.
# Uses CRSLDX EMA 10 and EMA 20 to identify the market regime.
# Tracks ENTRY, HOLD, and EXIT for each stock.
# Maintains complete trade history and performance.
# Automatically identifies the latest available review date.
# Generates separate Bullish and Bearish active-stock lists.
# Saves the latest stock lists as comma-separated TXT files.

# ============================================================
#                    CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
STOCK_LIST_FILE = str(BASE_DIR / "Futures Stock List.csv")
DATA_FOLDER = str(BASE_DIR / "MTF_FUTstocks_data" / "daily")
OUTPUT_FOLDER = str(BASE_DIR)

INDEX_SYMBOL = "^CRSLDX"

# Backtest starts from this review date
BACKTEST_START_DATE = "2025-10-10"

# Momentum return periods
LOOKBACK_25 = 25
LOOKBACK_50 = 50

# Entry / hold ranking rules
ENTRY_RANK = 30
EXIT_RANK = 40

# Market regime
EMA_FAST = 10
EMA_SLOW = 20


# ============================================================
#                    OUTPUT FILES
# ============================================================

BULLISH_TRADE_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_Bullish_Trade_History.csv"
)

BEARISH_TRADE_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_Bearish_Trade_History.csv"
)

BULLISH_CHANGES_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_Bullish_List_Changes.csv"
)

BEARISH_CHANGES_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_Bearish_List_Changes.csv"
)

BULLISH_REVIEW_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_Bullish_Review_History.csv"
)

BEARISH_REVIEW_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_Bearish_Review_History.csv"
)

COMBINED_REVIEW_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_Combined_Bullish_Bearish_Review_History.csv"
)

ACTIVE_SNAPSHOT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "01&16_Review_Date_Wise_Active_Stocks.csv"
)

BULLISH_CURRENT_ACTIVE_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_Bullish_Current_Active_Stocks_Backtest.csv"
)

BEARISH_CURRENT_ACTIVE_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_Bearish_Current_Active_Stocks_Backtest.csv"
)

MARKET_REGIME_FILE = os.path.join(
    OUTPUT_FOLDER,
    "z01&16_CRSLDX_Market_Regime_History.csv"
)

# Latest completed review-date active stock lists (comma-separated TXT)
BULLISH_LATEST_TXT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "01&16_Bullish_Latest_Review_Stocks.txt"
)

BEARISH_LATEST_TXT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "01&16_Bearish_Latest_Review_Stocks.txt"
)


# ============================================================
#                    HELPER FUNCTIONS
# ============================================================

def find_column(df, possible_names):
    """
    Find a column using multiple possible names.
    """

    mapping = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for name in possible_names:

        key = str(name).strip().lower()

        if key in mapping:
            return mapping[key]

    return None


def save_comma_separated_stock_list(stock_list, file_path):
    """
    Save stock symbols in one line separated only by commas.

    Example:
    RELIANCE,TCS,INFY,HDFCBANK
    """

    clean_stocks = []

    for stock in stock_list:
        stock = str(stock).strip()

        if stock:
            clean_stocks.append(stock)

    # Remove duplicates while preserving the existing order
    clean_stocks = list(dict.fromkeys(clean_stocks))

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(
            ",".join(clean_stocks)
        )

    return len(clean_stocks)


# ============================================================
#                    FIND CSV FILE
# ============================================================

def find_stock_file(stock):

    stock = str(stock).strip()

    possible_files = [
        f"{stock}.csv",
        f"{stock}.NS.csv",
    ]

    for filename in possible_files:

        path = os.path.join(
            DATA_FOLDER,
            filename
        )

        if os.path.exists(path):
            return path

    stock_upper = stock.upper()

    for filename in os.listdir(DATA_FOLDER):

        if not filename.lower().endswith(".csv"):
            continue

        base = os.path.splitext(filename)[0].upper()

        if base == stock_upper:
            return os.path.join(
                DATA_FOLDER,
                filename
            )

        if base == f"{stock_upper}.NS":
            return os.path.join(
                DATA_FOLDER,
                filename
            )

    return None


# ============================================================
#                    LOAD DAILY DATA
# ============================================================

def load_daily_file(file_path):

    df = pd.read_csv(file_path)

    date_col = find_column(
        df,
        [
            "Date",
            "Datetime",
            "Time"
        ]
    )

    open_col = find_column(
        df,
        ["Open"]
    )

    close_col = find_column(
        df,
        [
            "Close",
            "Adj Close",
            "Adj_Close"
        ]
    )

    if date_col is None:
        raise ValueError(
            f"Date column not found in {file_path}"
        )

    if open_col is None:
        raise ValueError(
            f"Open column not found in {file_path}"
        )

    if close_col is None:
        raise ValueError(
            f"Close column not found in {file_path}"
        )

    clean = pd.DataFrame()

    clean["Date"] = pd.to_datetime(
        df[date_col],
        errors="coerce"
    )

    clean["Open"] = pd.to_numeric(
        df[open_col],
        errors="coerce"
    )

    clean["Close"] = pd.to_numeric(
        df[close_col],
        errors="coerce"
    )

    clean = clean.dropna(
        subset=[
            "Date",
            "Open",
            "Close"
        ]
    )

    clean = clean.sort_values("Date")

    clean = clean.drop_duplicates(
        subset=["Date"],
        keep="last"
    )

    clean = clean.reset_index(drop=True)

    # --------------------------------------------------------
    # 25-session return
    # --------------------------------------------------------

    clean["Return_25_%"] = (
        (
            clean["Close"]
            / clean["Close"].shift(LOOKBACK_25)
        )
        - 1
    ) * 100

    # --------------------------------------------------------
    # 50-session return
    # --------------------------------------------------------

    clean["Return_50_%"] = (
        (
            clean["Close"]
            / clean["Close"].shift(LOOKBACK_50)
        )
        - 1
    ) * 100

    return clean


# ============================================================
#                    ADD INDEX EMAs
# ============================================================

def add_market_indicators(index_df):

    df = index_df.copy()

    df["EMA10"] = (
        df["Close"]
        .ewm(
            span=EMA_FAST,
            adjust=False
        )
        .mean()
    )

    df["EMA20"] = (
        df["Close"]
        .ewm(
            span=EMA_SLOW,
            adjust=False
        )
        .mean()
    )

    return df


# ============================================================
#                    MARKET REGIME
# ============================================================

def get_market_regime(row):

    ema10 = row["EMA10"]
    ema20 = row["EMA20"]

    if pd.isna(ema10) or pd.isna(ema20):
        return "NA"

    if ema10 > ema20:
        return "BULLISH"

    if ema10 < ema20:
        return "BEARISH"

    return "NEUTRAL"


# ============================================================
#                    STOCK LIST
# ============================================================

def get_stock_list():

    df = pd.read_csv(
        STOCK_LIST_FILE
    )

    stock_col = find_column(
        df,
        [
            "Stock",
            "Symbol",
            "Ticker",
            "Stock_Name",
            "Stock Name",
            "Name"
        ]
    )

    if stock_col is None:
        stock_col = df.columns[0]

    stocks = (
        df[stock_col]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    # Remove duplicate symbols while keeping order
    stocks = list(
        dict.fromkeys(stocks)
    )

    return stocks


# ============================================================
#                    LOAD ALL STOCKS
# ============================================================

def load_all_stock_data():

    stocks = get_stock_list()

    stock_data = {}

    print("\n" + "=" * 100)
    print("LOADING STOCK DATA")
    print("=" * 100)

    print(
        f"\nTotal stocks in futures list: "
        f"{len(stocks)}\n"
    )

    for i, stock in enumerate(
        stocks,
        start=1
    ):

        print(
            f"[{i}/{len(stocks)}] "
            f"Loading {stock}"
        )

        file_path = find_stock_file(stock)

        if file_path is None:

            print(
                "   -> FILE NOT FOUND"
            )

            continue

        try:

            df = load_daily_file(
                file_path
            )

            stock_data[
                stock.upper()
            ] = df

        except Exception as e:

            print(
                f"   -> ERROR: {e}"
            )

    print(
        f"\nSuccessfully loaded: "
        f"{len(stock_data)} stocks"
    )

    return stock_data


# ============================================================
#                    REVIEW DATES
# ============================================================

def generate_review_dates(
    start_date,
    end_date
):

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    review_dates = []

    current = pd.Timestamp(
        year=start.year,
        month=start.month,
        day=1
    )

    while current <= end:

        first = pd.Timestamp(
            year=current.year,
            month=current.month,
            day=1
        )

        sixteenth = pd.Timestamp(
            year=current.year,
            month=current.month,
            day=16
        )

        if (
            first >= start
            and first <= end
        ):
            review_dates.append(first)

        if (
            sixteenth >= start
            and sixteenth <= end
        ):
            review_dates.append(sixteenth)

        current = (
            current
            + pd.offsets.MonthBegin(1)
        )

    return sorted(
        list(set(review_dates))
    )


# ============================================================
#                    DATA CUTOFF
# ============================================================

def get_cutoff_date(review_date):

    review_date = pd.Timestamp(
        review_date
    )

    # --------------------------------------------------------
    # 1st review
    # Use data through previous month end
    # --------------------------------------------------------

    if review_date.day == 1:

        return (
            review_date
            - pd.Timedelta(days=1)
        )

    # --------------------------------------------------------
    # 16th review
    # Use data through 15th
    # --------------------------------------------------------

    return pd.Timestamp(
        year=review_date.year,
        month=review_date.month,
        day=15
    )


# ============================================================
#              GET LAST INDEX ROW BEFORE CUTOFF
# ============================================================

def get_last_row_until_date(
    df,
    cutoff_date
):

    eligible = df[
        df["Date"] <= cutoff_date
    ]

    if eligible.empty:
        return None

    return eligible.iloc[-1]


# ============================================================
#           GET STOCK ROW ON EXACT DATA DATE
# ============================================================

def get_exact_date_row(
    df,
    data_date
):

    eligible = df[
        df["Date"] == data_date
    ]

    if eligible.empty:
        return None

    return eligible.iloc[-1]


# ============================================================
#                    EXECUTION PRICE
# ============================================================

def get_execution_price(
    df,
    review_date
):
    """
    Entry/exit is at review-date open.

    If review date is holiday/weekend,
    use next available trading day's open.
    """

    eligible = df[
        df["Date"] >= review_date
    ]

    if eligible.empty:
        return None, None

    row = eligible.iloc[0]

    return (
        row["Date"],
        float(row["Open"])
    )


# ============================================================
#                   CALCULATE TRADE RETURN
# ============================================================

def bullish_trade_return(
    entry_price,
    exit_price
):

    return (
        (
            exit_price
            / entry_price
        )
        - 1
    ) * 100


def bearish_trade_return(
    entry_price,
    exit_price
):

    # Correct short percentage P/L
    return (
        (
            entry_price
            - exit_price
        )
        / entry_price
    ) * 100


# ============================================================
#                    MAIN BACKTEST
# ============================================================

def main():

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    print("\n")
    print("=" * 100)
    print(
        "25 / 50 SESSION MOMENTUM BACKTEST"
    )
    print(
        "BULLISH + BEARISH"
    )
    print("=" * 100)

    print(
        f"\nBacktest Start       : "
        f"{BACKTEST_START_DATE}"
    )

    print(
        "Review Frequency     : "
        "1st and 16th"
    )

    print(
        "Bullish Entry        : "
        "Top 30 in BOTH"
    )

    print(
        "Bearish Entry        : "
        "Bottom 30 in BOTH"
    )

    print(
        "Exit                 : "
        "Outside Top/Bottom 40 "
        "in EITHER ranking"
    )

    print(
        f"Market Regime        : "
        f"EMA{EMA_FAST} / EMA{EMA_SLOW} "
        f"on {INDEX_SYMBOL}"
    )


    # ========================================================
    # LOAD STOCK DATA
    # ========================================================

    stock_data = load_all_stock_data()


    # ========================================================
    # LOAD CRSLDX
    # ========================================================

    index_file = find_stock_file(
        INDEX_SYMBOL
    )

    if index_file is None:

        raise FileNotFoundError(
            f"\n{INDEX_SYMBOL} file not found "
            f"in:\n{DATA_FOLDER}"
        )


    index_df = load_daily_file(
        index_file
    )

    index_df = add_market_indicators(
        index_df
    )


    # ========================================================
    # DETERMINE END DATE
    # ========================================================

    end_date = index_df[
        "Date"
    ].max()


    # ========================================================
    # REVIEW DATES
    # ========================================================

    review_dates = generate_review_dates(
        BACKTEST_START_DATE,
        end_date
    )


    print(
        f"\nNumber of review dates: "
        f"{len(review_dates)}"
    )


    # ========================================================
    # ACTIVE POSITION DICTIONARIES
    # ========================================================

    bullish_active = {}
    bearish_active = {}


    # ========================================================
    # STORAGE
    # ========================================================

    bullish_trades = []
    bearish_trades = []

    bullish_changes = []
    bearish_changes = []

    bullish_review_history = []
    bearish_review_history = []

    active_snapshots = []

    market_regime_history = []


    # ========================================================
    # LOOP THROUGH REVIEW DATES
    # ========================================================

    for review_number, review_date in enumerate(
        review_dates,
        start=1
    ):

        cutoff_date = get_cutoff_date(
            review_date
        )

        print("\n")
        print("=" * 100)

        print(
            f"[{review_number}/"
            f"{len(review_dates)}]"
        )

        print(
            f"Review Date    : "
            f"{review_date.date()}"
        )

        print(
            f"Calendar Cutoff: "
            f"{cutoff_date.date()}"
        )


        # ====================================================
        # INDEX DATA
        # ====================================================

        index_row = get_last_row_until_date(
            index_df,
            cutoff_date
        )

        if index_row is None:

            print(
                "No CRSLDX data available."
            )

            continue


        actual_data_date = pd.Timestamp(
            index_row["Date"]
        )

        index_return_25 = index_row[
            "Return_25_%"
        ]

        index_return_50 = index_row[
            "Return_50_%"
        ]


        if (
            pd.isna(index_return_25)
            or
            pd.isna(index_return_50)
        ):

            print(
                "Not enough CRSLDX history "
                "for 25/50-session returns."
            )

            continue


        market_ema10 = float(
            index_row["EMA10"]
        )

        market_ema20 = float(
            index_row["EMA20"]
        )

        market_regime = (
            get_market_regime(
                index_row
            )
        )


        print(
            f"Actual Data Date: "
            f"{actual_data_date.date()}"
        )

        print(
            f"CRSLDX 25D     : "
            f"{index_return_25:.2f}%"
        )

        print(
            f"CRSLDX 50D     : "
            f"{index_return_50:.2f}%"
        )

        print(
            f"CRSLDX EMA10   : "
            f"{market_ema10:.2f}"
        )

        print(
            f"CRSLDX EMA20   : "
            f"{market_ema20:.2f}"
        )

        print(
            f"Market Regime  : "
            f"{market_regime}"
        )


        # ====================================================
        # SAVE MARKET REGIME
        # ====================================================

        market_regime_history.append(
            {
                "Review_Date":
                    review_date,

                "Calendar_Cutoff":
                    cutoff_date,

                "Actual_Data_Date":
                    actual_data_date,

                "CRSLDX_Close":
                    index_row["Close"],

                "CRSLDX_Return_25_%":
                    index_return_25,

                "CRSLDX_Return_50_%":
                    index_return_50,

                "CRSLDX_EMA10":
                    market_ema10,

                "CRSLDX_EMA20":
                    market_ema20,

                "Market_Regime":
                    market_regime,
            }
        )


        # ====================================================
        # BUILD RANKING TABLE
        # ====================================================

        rows = []


        for stock, stock_df in (
            stock_data.items()
        ):

            # IMPORTANT:
            # Only use stocks that actually traded on the same
            # data date as CRSLDX.
            #
            # This prevents stale stock prices being ranked.

            row = get_exact_date_row(
                stock_df,
                actual_data_date
            )

            if row is None:
                continue


            return25 = row[
                "Return_25_%"
            ]

            return50 = row[
                "Return_50_%"
            ]


            if (
                pd.isna(return25)
                or
                pd.isna(return50)
            ):
                continue


            rows.append(
                {
                    "Stock":
                        stock,

                    "Data_Date":
                        actual_data_date,

                    "Close":
                        row["Close"],

                    "Return_25_%":
                        float(return25),

                    "Return_50_%":
                        float(return50),
                }
            )


        if not rows:

            print(
                "No valid stocks available "
                "for ranking."
            )

            continue


        ranking_df = pd.DataFrame(
            rows
        )


        # ====================================================
        # BULLISH RANKINGS
        # ====================================================

        ranking_df[
            "Bull_Rank_25"
        ] = (
            ranking_df[
                "Return_25_%"
            ]
            .rank(
                method="min",
                ascending=False
            )
            .astype(int)
        )


        ranking_df[
            "Bull_Rank_50"
        ] = (
            ranking_df[
                "Return_50_%"
            ]
            .rank(
                method="min",
                ascending=False
            )
            .astype(int)
        )


        # ====================================================
        # BEARISH RANKINGS
        # ====================================================

        ranking_df[
            "Bear_Rank_25"
        ] = (
            ranking_df[
                "Return_25_%"
            ]
            .rank(
                method="min",
                ascending=True
            )
            .astype(int)
        )


        ranking_df[
            "Bear_Rank_50"
        ] = (
            ranking_df[
                "Return_50_%"
            ]
            .rank(
                method="min",
                ascending=True
            )
            .astype(int)
        )


        # ====================================================
        # RELATIVE RETURN VS INDEX
        # ====================================================

        ranking_df[
            "Vs_CRSLDX_25_%"
        ] = (
            ranking_df[
                "Return_25_%"
            ]
            - index_return_25
        )


        ranking_df[
            "Vs_CRSLDX_50_%"
        ] = (
            ranking_df[
                "Return_50_%"
            ]
            - index_return_50
        )


        # ====================================================
        # STORE STATUS GENERATED THIS REVIEW
        # ====================================================

        bullish_status = {}
        bearish_status = {}


        # ====================================================
        # PROCESS EVERY STOCK
        # ====================================================

        for _, row in ranking_df.iterrows():

            stock = row["Stock"]

            stock_df = stock_data[
                stock
            ]


            # =================================================
            # BULLISH CONDITIONS
            # =================================================

            bullish_entry_condition = (

                row["Bull_Rank_25"]
                <= ENTRY_RANK

                and

                row["Bull_Rank_50"]
                <= ENTRY_RANK

                and

                row["Return_25_%"]
                > index_return_25

                and

                row["Return_50_%"]
                > index_return_50
            )


            bullish_exit_condition = (

                row["Bull_Rank_25"]
                > EXIT_RANK

                or

                row["Bull_Rank_50"]
                > EXIT_RANK
            )


            # =================================================
            # BULLISH - ALREADY ACTIVE
            # =================================================

            if stock in bullish_active:

                if bullish_exit_condition:

                    (
                        execution_date,
                        execution_price
                    ) = get_execution_price(
                        stock_df,
                        review_date
                    )


                    if execution_date is not None:

                        entry = bullish_active[
                            stock
                        ]


                        trade_return = (
                            bullish_trade_return(
                                entry[
                                    "Entry_Price"
                                ],
                                execution_price
                            )
                        )


                        holding_days = (
                            execution_date
                            - entry["Entry_Date"]
                        ).days


                        bullish_trades.append(
                            {
                                "Theme":
                                    "BULLISH",

                                "Stock":
                                    stock,

                                # -------------------------
                                # ENTRY
                                # -------------------------

                                "Entry_Review_Date":
                                    entry[
                                        "Entry_Review_Date"
                                    ],

                                "Entry_Data_Date":
                                    entry[
                                        "Entry_Data_Date"
                                    ],

                                "Entry_Date":
                                    entry[
                                        "Entry_Date"
                                    ],

                                "Entry_Price":
                                    entry[
                                        "Entry_Price"
                                    ],

                                "Entry_Rank_25":
                                    entry[
                                        "Entry_Rank_25"
                                    ],

                                "Entry_Rank_50":
                                    entry[
                                        "Entry_Rank_50"
                                    ],

                                "Entry_Return_25_%":
                                    entry[
                                        "Entry_Return_25_%"
                                    ],

                                "Entry_Return_50_%":
                                    entry[
                                        "Entry_Return_50_%"
                                    ],

                                "Entry_Vs_CRSLDX_25_%":
                                    entry[
                                        "Entry_Vs_CRSLDX_25_%"
                                    ],

                                "Entry_Vs_CRSLDX_50_%":
                                    entry[
                                        "Entry_Vs_CRSLDX_50_%"
                                    ],

                                "Entry_CRSLDX_Return_25_%":
                                    entry[
                                        "Entry_CRSLDX_Return_25_%"
                                    ],

                                "Entry_CRSLDX_Return_50_%":
                                    entry[
                                        "Entry_CRSLDX_Return_50_%"
                                    ],

                                "Entry_CRSLDX_EMA10":
                                    entry[
                                        "Entry_CRSLDX_EMA10"
                                    ],

                                "Entry_CRSLDX_EMA20":
                                    entry[
                                        "Entry_CRSLDX_EMA20"
                                    ],

                                "Entry_Market_Regime":
                                    entry[
                                        "Entry_Market_Regime"
                                    ],

                                # -------------------------
                                # EXIT
                                # -------------------------

                                "Exit_Review_Date":
                                    review_date,

                                "Exit_Data_Date":
                                    actual_data_date,

                                "Exit_Date":
                                    execution_date,

                                "Exit_Price":
                                    execution_price,

                                "Exit_Rank_25":
                                    row[
                                        "Bull_Rank_25"
                                    ],

                                "Exit_Rank_50":
                                    row[
                                        "Bull_Rank_50"
                                    ],

                                "Exit_Return_25_%":
                                    row[
                                        "Return_25_%"
                                    ],

                                "Exit_Return_50_%":
                                    row[
                                        "Return_50_%"
                                    ],

                                "Exit_Vs_CRSLDX_25_%":
                                    row[
                                        "Vs_CRSLDX_25_%"
                                    ],

                                "Exit_Vs_CRSLDX_50_%":
                                    row[
                                        "Vs_CRSLDX_50_%"
                                    ],

                                "Exit_CRSLDX_Return_25_%":
                                    index_return_25,

                                "Exit_CRSLDX_Return_50_%":
                                    index_return_50,

                                "Exit_CRSLDX_EMA10":
                                    market_ema10,

                                "Exit_CRSLDX_EMA20":
                                    market_ema20,

                                "Exit_Market_Regime":
                                    market_regime,

                                # -------------------------
                                # RESULT
                                # -------------------------

                                "Holding_Days":
                                    holding_days,

                                "Stock_Return_%":
                                    trade_return,
                            }
                        )


                        bullish_changes.append(
                            {
                                "Theme":
                                    "BULLISH",

                                "Stock":
                                    stock,

                                "Event":
                                    "EXIT",

                                "Review_Date":
                                    review_date,

                                "Data_Date":
                                    actual_data_date,

                                "Execution_Date":
                                    execution_date,

                                "Execution_Price":
                                    execution_price,

                                "Rank_25":
                                    row[
                                        "Bull_Rank_25"
                                    ],

                                "Rank_50":
                                    row[
                                        "Bull_Rank_50"
                                    ],

                                "Return_25_%":
                                    row[
                                        "Return_25_%"
                                    ],

                                "Return_50_%":
                                    row[
                                        "Return_50_%"
                                    ],

                                "Vs_CRSLDX_25_%":
                                    row[
                                        "Vs_CRSLDX_25_%"
                                    ],

                                "Vs_CRSLDX_50_%":
                                    row[
                                        "Vs_CRSLDX_50_%"
                                    ],

                                "Market_Regime":
                                    market_regime,
                            }
                        )


                        bullish_status[
                            stock
                        ] = "EXIT"


                        del bullish_active[
                            stock
                        ]


                else:

                    bullish_status[
                        stock
                    ] = "HOLD"


            # =================================================
            # BULLISH - NEW ENTRY
            # =================================================

            else:

                if bullish_entry_condition:

                    (
                        execution_date,
                        execution_price
                    ) = get_execution_price(
                        stock_df,
                        review_date
                    )


                    if execution_date is not None:

                        bullish_active[
                            stock
                        ] = {

                            "Entry_Review_Date":
                                review_date,

                            "Entry_Data_Date":
                                actual_data_date,

                            "Entry_Date":
                                execution_date,

                            "Entry_Price":
                                execution_price,

                            "Entry_Rank_25":
                                int(
                                    row[
                                        "Bull_Rank_25"
                                    ]
                                ),

                            "Entry_Rank_50":
                                int(
                                    row[
                                        "Bull_Rank_50"
                                    ]
                                ),

                            "Entry_Return_25_%":
                                row[
                                    "Return_25_%"
                                ],

                            "Entry_Return_50_%":
                                row[
                                    "Return_50_%"
                                ],

                            "Entry_Vs_CRSLDX_25_%":
                                row[
                                    "Vs_CRSLDX_25_%"
                                ],

                            "Entry_Vs_CRSLDX_50_%":
                                row[
                                    "Vs_CRSLDX_50_%"
                                ],

                            "Entry_CRSLDX_Return_25_%":
                                index_return_25,

                            "Entry_CRSLDX_Return_50_%":
                                index_return_50,

                            "Entry_CRSLDX_EMA10":
                                market_ema10,

                            "Entry_CRSLDX_EMA20":
                                market_ema20,

                            "Entry_Market_Regime":
                                market_regime,
                        }


                        bullish_changes.append(
                            {
                                "Theme":
                                    "BULLISH",

                                "Stock":
                                    stock,

                                "Event":
                                    "ENTRY",

                                "Review_Date":
                                    review_date,

                                "Data_Date":
                                    actual_data_date,

                                "Execution_Date":
                                    execution_date,

                                "Execution_Price":
                                    execution_price,

                                "Rank_25":
                                    row[
                                        "Bull_Rank_25"
                                    ],

                                "Rank_50":
                                    row[
                                        "Bull_Rank_50"
                                    ],

                                "Return_25_%":
                                    row[
                                        "Return_25_%"
                                    ],

                                "Return_50_%":
                                    row[
                                        "Return_50_%"
                                    ],

                                "Vs_CRSLDX_25_%":
                                    row[
                                        "Vs_CRSLDX_25_%"
                                    ],

                                "Vs_CRSLDX_50_%":
                                    row[
                                        "Vs_CRSLDX_50_%"
                                    ],

                                "Market_Regime":
                                    market_regime,
                            }
                        )


                        bullish_status[
                            stock
                        ] = "ENTRY"

                else:

                    bullish_status[
                        stock
                    ] = "NOT_ACTIVE"


            # =================================================
            # BEARISH CONDITIONS
            # =================================================

            bearish_entry_condition = (

                row["Bear_Rank_25"]
                <= ENTRY_RANK

                and

                row["Bear_Rank_50"]
                <= ENTRY_RANK

                and

                row["Return_25_%"]
                < index_return_25

                and

                row["Return_50_%"]
                < index_return_50
            )


            bearish_exit_condition = (

                row["Bear_Rank_25"]
                > EXIT_RANK

                or

                row["Bear_Rank_50"]
                > EXIT_RANK
            )


            # =================================================
            # BEARISH - ALREADY ACTIVE
            # =================================================

            if stock in bearish_active:

                if bearish_exit_condition:

                    (
                        execution_date,
                        execution_price
                    ) = get_execution_price(
                        stock_df,
                        review_date
                    )


                    if execution_date is not None:

                        entry = bearish_active[
                            stock
                        ]


                        trade_return = (
                            bearish_trade_return(
                                entry[
                                    "Entry_Price"
                                ],
                                execution_price
                            )
                        )


                        holding_days = (
                            execution_date
                            - entry[
                                "Entry_Date"
                            ]
                        ).days


                        bearish_trades.append(
                            {
                                "Theme":
                                    "BEARISH",

                                "Stock":
                                    stock,

                                # -------------------------
                                # ENTRY
                                # -------------------------

                                "Entry_Review_Date":
                                    entry[
                                        "Entry_Review_Date"
                                    ],

                                "Entry_Data_Date":
                                    entry[
                                        "Entry_Data_Date"
                                    ],

                                "Entry_Date":
                                    entry[
                                        "Entry_Date"
                                    ],

                                "Entry_Price":
                                    entry[
                                        "Entry_Price"
                                    ],

                                "Entry_Rank_25":
                                    entry[
                                        "Entry_Rank_25"
                                    ],

                                "Entry_Rank_50":
                                    entry[
                                        "Entry_Rank_50"
                                    ],

                                "Entry_Return_25_%":
                                    entry[
                                        "Entry_Return_25_%"
                                    ],

                                "Entry_Return_50_%":
                                    entry[
                                        "Entry_Return_50_%"
                                    ],

                                "Entry_Vs_CRSLDX_25_%":
                                    entry[
                                        "Entry_Vs_CRSLDX_25_%"
                                    ],

                                "Entry_Vs_CRSLDX_50_%":
                                    entry[
                                        "Entry_Vs_CRSLDX_50_%"
                                    ],

                                "Entry_CRSLDX_Return_25_%":
                                    entry[
                                        "Entry_CRSLDX_Return_25_%"
                                    ],

                                "Entry_CRSLDX_Return_50_%":
                                    entry[
                                        "Entry_CRSLDX_Return_50_%"
                                    ],

                                "Entry_CRSLDX_EMA10":
                                    entry[
                                        "Entry_CRSLDX_EMA10"
                                    ],

                                "Entry_CRSLDX_EMA20":
                                    entry[
                                        "Entry_CRSLDX_EMA20"
                                    ],

                                "Entry_Market_Regime":
                                    entry[
                                        "Entry_Market_Regime"
                                    ],

                                # -------------------------
                                # EXIT
                                # -------------------------

                                "Exit_Review_Date":
                                    review_date,

                                "Exit_Data_Date":
                                    actual_data_date,

                                "Exit_Date":
                                    execution_date,

                                "Exit_Price":
                                    execution_price,

                                "Exit_Rank_25":
                                    row[
                                        "Bear_Rank_25"
                                    ],

                                "Exit_Rank_50":
                                    row[
                                        "Bear_Rank_50"
                                    ],

                                "Exit_Return_25_%":
                                    row[
                                        "Return_25_%"
                                    ],

                                "Exit_Return_50_%":
                                    row[
                                        "Return_50_%"
                                    ],

                                "Exit_Vs_CRSLDX_25_%":
                                    row[
                                        "Vs_CRSLDX_25_%"
                                    ],

                                "Exit_Vs_CRSLDX_50_%":
                                    row[
                                        "Vs_CRSLDX_50_%"
                                    ],

                                "Exit_CRSLDX_Return_25_%":
                                    index_return_25,

                                "Exit_CRSLDX_Return_50_%":
                                    index_return_50,

                                "Exit_CRSLDX_EMA10":
                                    market_ema10,

                                "Exit_CRSLDX_EMA20":
                                    market_ema20,

                                "Exit_Market_Regime":
                                    market_regime,

                                # -------------------------
                                # RESULT
                                # -------------------------

                                "Holding_Days":
                                    holding_days,

                                "Stock_Return_%":
                                    trade_return,
                            }
                        )


                        bearish_changes.append(
                            {
                                "Theme":
                                    "BEARISH",

                                "Stock":
                                    stock,

                                "Event":
                                    "EXIT",

                                "Review_Date":
                                    review_date,

                                "Data_Date":
                                    actual_data_date,

                                "Execution_Date":
                                    execution_date,

                                "Execution_Price":
                                    execution_price,

                                "Rank_25":
                                    row[
                                        "Bear_Rank_25"
                                    ],

                                "Rank_50":
                                    row[
                                        "Bear_Rank_50"
                                    ],

                                "Return_25_%":
                                    row[
                                        "Return_25_%"
                                    ],

                                "Return_50_%":
                                    row[
                                        "Return_50_%"
                                    ],

                                "Vs_CRSLDX_25_%":
                                    row[
                                        "Vs_CRSLDX_25_%"
                                    ],

                                "Vs_CRSLDX_50_%":
                                    row[
                                        "Vs_CRSLDX_50_%"
                                    ],

                                "Market_Regime":
                                    market_regime,
                            }
                        )


                        bearish_status[
                            stock
                        ] = "EXIT"


                        del bearish_active[
                            stock
                        ]


                else:

                    bearish_status[
                        stock
                    ] = "HOLD"


            # =================================================
            # BEARISH - NEW ENTRY
            # =================================================

            else:

                if bearish_entry_condition:

                    (
                        execution_date,
                        execution_price
                    ) = get_execution_price(
                        stock_df,
                        review_date
                    )


                    if execution_date is not None:

                        bearish_active[
                            stock
                        ] = {

                            "Entry_Review_Date":
                                review_date,

                            "Entry_Data_Date":
                                actual_data_date,

                            "Entry_Date":
                                execution_date,

                            "Entry_Price":
                                execution_price,

                            "Entry_Rank_25":
                                int(
                                    row[
                                        "Bear_Rank_25"
                                    ]
                                ),

                            "Entry_Rank_50":
                                int(
                                    row[
                                        "Bear_Rank_50"
                                    ]
                                ),

                            "Entry_Return_25_%":
                                row[
                                    "Return_25_%"
                                ],

                            "Entry_Return_50_%":
                                row[
                                    "Return_50_%"
                                ],

                            "Entry_Vs_CRSLDX_25_%":
                                row[
                                    "Vs_CRSLDX_25_%"
                                ],

                            "Entry_Vs_CRSLDX_50_%":
                                row[
                                    "Vs_CRSLDX_50_%"
                                ],

                            "Entry_CRSLDX_Return_25_%":
                                index_return_25,

                            "Entry_CRSLDX_Return_50_%":
                                index_return_50,

                            "Entry_CRSLDX_EMA10":
                                market_ema10,

                            "Entry_CRSLDX_EMA20":
                                market_ema20,

                            "Entry_Market_Regime":
                                market_regime,
                        }


                        bearish_changes.append(
                            {
                                "Theme":
                                    "BEARISH",

                                "Stock":
                                    stock,

                                "Event":
                                    "ENTRY",

                                "Review_Date":
                                    review_date,

                                "Data_Date":
                                    actual_data_date,

                                "Execution_Date":
                                    execution_date,

                                "Execution_Price":
                                    execution_price,

                                "Rank_25":
                                    row[
                                        "Bear_Rank_25"
                                    ],

                                "Rank_50":
                                    row[
                                        "Bear_Rank_50"
                                    ],

                                "Return_25_%":
                                    row[
                                        "Return_25_%"
                                    ],

                                "Return_50_%":
                                    row[
                                        "Return_50_%"
                                    ],

                                "Vs_CRSLDX_25_%":
                                    row[
                                        "Vs_CRSLDX_25_%"
                                    ],

                                "Vs_CRSLDX_50_%":
                                    row[
                                        "Vs_CRSLDX_50_%"
                                    ],

                                "Market_Regime":
                                    market_regime,
                            }
                        )


                        bearish_status[
                            stock
                        ] = "ENTRY"

                else:

                    bearish_status[
                        stock
                    ] = "NOT_ACTIVE"


        # ====================================================
        # COMPLETE REVIEW HISTORY
        # ====================================================

        for _, row in ranking_df.iterrows():

            stock = row["Stock"]


            # ------------------------------------------------
            # BULLISH HISTORY
            # ------------------------------------------------

            bull_status = bullish_status.get(
                stock,
                "NOT_ACTIVE"
            )

            bullish_review_history.append(
                {
                    "Review_Date":
                        review_date,

                    "Calendar_Cutoff":
                        cutoff_date,

                    "Actual_Data_Date":
                        actual_data_date,

                    "Stock":
                        stock,

                    "Return_25_%":
                        row[
                            "Return_25_%"
                        ],

                    "Return_50_%":
                        row[
                            "Return_50_%"
                        ],

                    "Rank_25":
                        row[
                            "Bull_Rank_25"
                        ],

                    "Rank_50":
                        row[
                            "Bull_Rank_50"
                        ],

                    "Vs_CRSLDX_25_%":
                        row[
                            "Vs_CRSLDX_25_%"
                        ],

                    "Vs_CRSLDX_50_%":
                        row[
                            "Vs_CRSLDX_50_%"
                        ],

                    "CRSLDX_Return_25_%":
                        index_return_25,

                    "CRSLDX_Return_50_%":
                        index_return_50,

                    "CRSLDX_EMA10":
                        market_ema10,

                    "CRSLDX_EMA20":
                        market_ema20,

                    "Market_Regime":
                        market_regime,

                    "Status":
                        bull_status,

                    "Active_After_Review":
                        stock
                        in bullish_active,
                }
            )


            # ------------------------------------------------
            # BEARISH HISTORY
            # ------------------------------------------------

            bear_status = bearish_status.get(
                stock,
                "NOT_ACTIVE"
            )

            bearish_review_history.append(
                {
                    "Review_Date":
                        review_date,

                    "Calendar_Cutoff":
                        cutoff_date,

                    "Actual_Data_Date":
                        actual_data_date,

                    "Stock":
                        stock,

                    "Return_25_%":
                        row[
                            "Return_25_%"
                        ],

                    "Return_50_%":
                        row[
                            "Return_50_%"
                        ],

                    "Rank_25":
                        row[
                            "Bear_Rank_25"
                        ],

                    "Rank_50":
                        row[
                            "Bear_Rank_50"
                        ],

                    "Vs_CRSLDX_25_%":
                        row[
                            "Vs_CRSLDX_25_%"
                        ],

                    "Vs_CRSLDX_50_%":
                        row[
                            "Vs_CRSLDX_50_%"
                        ],

                    "CRSLDX_Return_25_%":
                        index_return_25,

                    "CRSLDX_Return_50_%":
                        index_return_50,

                    "CRSLDX_EMA10":
                        market_ema10,

                    "CRSLDX_EMA20":
                        market_ema20,

                    "Market_Regime":
                        market_regime,

                    "Status":
                        bear_status,

                    "Active_After_Review":
                        stock
                        in bearish_active,
                }
            )


        # ====================================================
        # ACTIVE STOCK SNAPSHOT AFTER REVIEW
        # ====================================================

        ranking_lookup = (
            ranking_df
            .set_index("Stock")
        )


        # ----------------------------------------------------
        # BULLISH ACTIVE
        # ----------------------------------------------------

        for stock, info in (
            bullish_active.items()
        ):

            if stock not in ranking_lookup.index:
                continue


            row = ranking_lookup.loc[
                stock
            ]


            active_snapshots.append(
                {
                    "Review_Date":
                        review_date,

                    "Data_Date":
                        actual_data_date,

                    "Theme":
                        "BULLISH",

                    "Stock":
                        stock,

                    "Status_This_Review":
                        bullish_status.get(
                            stock,
                            "HOLD"
                        ),

                    "Rank_25":
                        row[
                            "Bull_Rank_25"
                        ],

                    "Rank_50":
                        row[
                            "Bull_Rank_50"
                        ],

                    "Return_25_%":
                        row[
                            "Return_25_%"
                        ],

                    "Return_50_%":
                        row[
                            "Return_50_%"
                        ],

                    "Vs_CRSLDX_25_%":
                        row[
                            "Vs_CRSLDX_25_%"
                        ],

                    "Vs_CRSLDX_50_%":
                        row[
                            "Vs_CRSLDX_50_%"
                        ],

                    "Entry_Review_Date":
                        info[
                            "Entry_Review_Date"
                        ],

                    "Entry_Date":
                        info[
                            "Entry_Date"
                        ],

                    "Entry_Price":
                        info[
                            "Entry_Price"
                        ],

                    "Market_Regime":
                        market_regime,
                }
            )


        # ----------------------------------------------------
        # BEARISH ACTIVE
        # ----------------------------------------------------

        for stock, info in (
            bearish_active.items()
        ):

            if stock not in ranking_lookup.index:
                continue


            row = ranking_lookup.loc[
                stock
            ]


            active_snapshots.append(
                {
                    "Review_Date":
                        review_date,

                    "Data_Date":
                        actual_data_date,

                    "Theme":
                        "BEARISH",

                    "Stock":
                        stock,

                    "Status_This_Review":
                        bearish_status.get(
                            stock,
                            "HOLD"
                        ),

                    "Rank_25":
                        row[
                            "Bear_Rank_25"
                        ],

                    "Rank_50":
                        row[
                            "Bear_Rank_50"
                        ],

                    "Return_25_%":
                        row[
                            "Return_25_%"
                        ],

                    "Return_50_%":
                        row[
                            "Return_50_%"
                        ],

                    "Vs_CRSLDX_25_%":
                        row[
                            "Vs_CRSLDX_25_%"
                        ],

                    "Vs_CRSLDX_50_%":
                        row[
                            "Vs_CRSLDX_50_%"
                        ],

                    "Entry_Review_Date":
                        info[
                            "Entry_Review_Date"
                        ],

                    "Entry_Date":
                        info[
                            "Entry_Date"
                        ],

                    "Entry_Price":
                        info[
                            "Entry_Price"
                        ],

                    "Market_Regime":
                        market_regime,
                }
            )


        # ====================================================
        # TERMINAL REVIEW SUMMARY
        # ====================================================

        bull_entries = sum(
            1
            for status
            in bullish_status.values()
            if status == "ENTRY"
        )

        bull_exits = sum(
            1
            for status
            in bullish_status.values()
            if status == "EXIT"
        )

        bear_entries = sum(
            1
            for status
            in bearish_status.values()
            if status == "ENTRY"
        )

        bear_exits = sum(
            1
            for status
            in bearish_status.values()
            if status == "EXIT"
        )


        print(
            f"\nBullish Entries : "
            f"{bull_entries}"
        )

        print(
            f"Bullish Exits   : "
            f"{bull_exits}"
        )

        print(
            f"Bullish Active  : "
            f"{len(bullish_active)}"
        )


        print(
            f"\nBearish Entries : "
            f"{bear_entries}"
        )

        print(
            f"Bearish Exits   : "
            f"{bear_exits}"
        )

        print(
            f"Bearish Active  : "
            f"{len(bearish_active)}"
        )


    # ========================================================
    # CONVERT TO DATAFRAMES
    # ========================================================

    bullish_trade_df = pd.DataFrame(
        bullish_trades
    )

    bearish_trade_df = pd.DataFrame(
        bearish_trades
    )

    bullish_changes_df = pd.DataFrame(
        bullish_changes
    )

    bearish_changes_df = pd.DataFrame(
        bearish_changes
    )

    bullish_review_df = pd.DataFrame(
        bullish_review_history
    )

    bearish_review_df = pd.DataFrame(
        bearish_review_history
    )

    active_snapshot_df = pd.DataFrame(
        active_snapshots
    )

    market_regime_df = pd.DataFrame(
        market_regime_history
    )


    # ========================================================
    # CURRENT ACTIVE BULLISH
    # ========================================================

    bullish_current_rows = []


    if not bullish_review_df.empty:

        latest_review_date = (
            bullish_review_df[
                "Review_Date"
            ].max()
        )

        latest_bull_df = (
            bullish_review_df[
                bullish_review_df[
                    "Review_Date"
                ] == latest_review_date
            ]
            .copy()
        )


        latest_bull_lookup = (
            latest_bull_df
            .set_index("Stock")
        )


        for stock, info in (
            bullish_active.items()
        ):

            if (
                stock
                not in latest_bull_lookup.index
            ):
                continue


            row = latest_bull_lookup.loc[
                stock
            ]


            bullish_current_rows.append(
                {
                    "Theme":
                        "BULLISH",

                    "Stock":
                        stock,

                    "Latest_Review_Date":
                        latest_review_date,

                    "Entry_Review_Date":
                        info[
                            "Entry_Review_Date"
                        ],

                    "Entry_Date":
                        info[
                            "Entry_Date"
                        ],

                    "Entry_Price":
                        info[
                            "Entry_Price"
                        ],

                    "Current_Rank_25":
                        row[
                            "Rank_25"
                        ],

                    "Current_Rank_50":
                        row[
                            "Rank_50"
                        ],

                    "Current_Return_25_%":
                        row[
                            "Return_25_%"
                        ],

                    "Current_Return_50_%":
                        row[
                            "Return_50_%"
                        ],

                    "Current_Vs_CRSLDX_25_%":
                        row[
                            "Vs_CRSLDX_25_%"
                        ],

                    "Current_Vs_CRSLDX_50_%":
                        row[
                            "Vs_CRSLDX_50_%"
                        ],

                    "Entry_Market_Regime":
                        info[
                            "Entry_Market_Regime"
                        ],

                    "Current_Market_Regime":
                        row[
                            "Market_Regime"
                        ],
                }
            )


    bullish_current_df = pd.DataFrame(
        bullish_current_rows
    )


    # ========================================================
    # CURRENT ACTIVE BEARISH
    # ========================================================

    bearish_current_rows = []


    if not bearish_review_df.empty:

        latest_review_date = (
            bearish_review_df[
                "Review_Date"
            ].max()
        )

        latest_bear_df = (
            bearish_review_df[
                bearish_review_df[
                    "Review_Date"
                ] == latest_review_date
            ]
            .copy()
        )


        latest_bear_lookup = (
            latest_bear_df
            .set_index("Stock")
        )


        for stock, info in (
            bearish_active.items()
        ):

            if (
                stock
                not in latest_bear_lookup.index
            ):
                continue


            row = latest_bear_lookup.loc[
                stock
            ]


            bearish_current_rows.append(
                {
                    "Theme":
                        "BEARISH",

                    "Stock":
                        stock,

                    "Latest_Review_Date":
                        latest_review_date,

                    "Entry_Review_Date":
                        info[
                            "Entry_Review_Date"
                        ],

                    "Entry_Date":
                        info[
                            "Entry_Date"
                        ],

                    "Entry_Price":
                        info[
                            "Entry_Price"
                        ],

                    "Current_Rank_25":
                        row[
                            "Rank_25"
                        ],

                    "Current_Rank_50":
                        row[
                            "Rank_50"
                        ],

                    "Current_Return_25_%":
                        row[
                            "Return_25_%"
                        ],

                    "Current_Return_50_%":
                        row[
                            "Return_50_%"
                        ],

                    "Current_Vs_CRSLDX_25_%":
                        row[
                            "Vs_CRSLDX_25_%"
                        ],

                    "Current_Vs_CRSLDX_50_%":
                        row[
                            "Vs_CRSLDX_50_%"
                        ],

                    "Entry_Market_Regime":
                        info[
                            "Entry_Market_Regime"
                        ],

                    "Current_Market_Regime":
                        row[
                            "Market_Regime"
                        ],
                }
            )


    bearish_current_df = pd.DataFrame(
        bearish_current_rows
    )


    # ========================================================
    # COMBINED REVIEW HISTORY
    # ========================================================

    combined_frames = []


    if not bullish_review_df.empty:

        temp = bullish_review_df.copy()

        temp.insert(
            1,
            "Theme",
            "BULLISH"
        )

        combined_frames.append(temp)


    if not bearish_review_df.empty:

        temp = bearish_review_df.copy()

        temp.insert(
            1,
            "Theme",
            "BEARISH"
        )

        combined_frames.append(temp)


    if combined_frames:

        combined_review_df = pd.concat(
            combined_frames,
            ignore_index=True
        )

    else:

        combined_review_df = (
            pd.DataFrame()
        )


    # ========================================================
    # ROUND NUMERIC VALUES
    # ========================================================

    all_dataframes = [
        bullish_trade_df,
        bearish_trade_df,
        bullish_changes_df,
        bearish_changes_df,
        bullish_review_df,
        bearish_review_df,
        combined_review_df,
        active_snapshot_df,
        bullish_current_df,
        bearish_current_df,
        market_regime_df,
    ]


    for df in all_dataframes:

        if df.empty:
            continue

        numeric_columns = (
            df.select_dtypes(
                include=[
                    np.number
                ]
            ).columns
        )

        df[numeric_columns] = (
            df[numeric_columns]
            .round(2)
        )


    # ========================================================
    # SAVE RESULTS
    # ========================================================

    bullish_trade_df.to_csv(
        BULLISH_TRADE_FILE,
        index=False
    )

    bearish_trade_df.to_csv(
        BEARISH_TRADE_FILE,
        index=False
    )

    bullish_changes_df.to_csv(
        BULLISH_CHANGES_FILE,
        index=False
    )

    bearish_changes_df.to_csv(
        BEARISH_CHANGES_FILE,
        index=False
    )

    bullish_review_df.to_csv(
        BULLISH_REVIEW_FILE,
        index=False
    )

    bearish_review_df.to_csv(
        BEARISH_REVIEW_FILE,
        index=False
    )

    combined_review_df.to_csv(
        COMBINED_REVIEW_FILE,
        index=False
    )

    active_snapshot_df.to_csv(
        ACTIVE_SNAPSHOT_FILE,
        index=False
    )

    bullish_current_df.to_csv(
        BULLISH_CURRENT_ACTIVE_FILE,
        index=False
    )

    bearish_current_df.to_csv(
        BEARISH_CURRENT_ACTIVE_FILE,
        index=False
    )

    market_regime_df.to_csv(
        MARKET_REGIME_FILE,
        index=False
    )


    # ========================================================
    # SAVE LATEST REVIEW-DATE STOCK LISTS AS TXT
    # ========================================================
    #
    # Example:
    # If the script is run on 04-09-2026 and the latest completed
    # review is 01-09-2026, these TXT files contain ONLY the
    # active BULLISH / BEARISH stocks from the 01-09-2026 review.
    #
    # Format is exactly one comma-separated line, with no spaces:
    # STOCK1,STOCK2,STOCK3
    # ========================================================

    latest_review_for_txt = None
    bullish_latest_count = 0
    bearish_latest_count = 0

    if not active_snapshot_df.empty:

        active_snapshot_df[
            "Review_Date"
        ] = pd.to_datetime(
            active_snapshot_df[
                "Review_Date"
            ],
            errors="coerce"
        )

        valid_review_dates = (
            active_snapshot_df[
                "Review_Date"
            ]
            .dropna()
        )

        if not valid_review_dates.empty:

            latest_review_for_txt = (
                valid_review_dates.max()
            )

            latest_snapshot_df = (
                active_snapshot_df[
                    active_snapshot_df[
                        "Review_Date"
                    ] == latest_review_for_txt
                ]
                .copy()
            )

            bullish_latest_stocks = (
                latest_snapshot_df.loc[
                    latest_snapshot_df[
                        "Theme"
                    ].astype(str).str.upper() == "BULLISH",
                    "Stock"
                ]
                .astype(str)
                .str.strip()
                .tolist()
            )

            bearish_latest_stocks = (
                latest_snapshot_df.loc[
                    latest_snapshot_df[
                        "Theme"
                    ].astype(str).str.upper() == "BEARISH",
                    "Stock"
                ]
                .astype(str)
                .str.strip()
                .tolist()
            )

            bullish_latest_count = (
                save_comma_separated_stock_list(
                    bullish_latest_stocks,
                    BULLISH_LATEST_TXT_FILE
                )
            )

            bearish_latest_count = (
                save_comma_separated_stock_list(
                    bearish_latest_stocks,
                    BEARISH_LATEST_TXT_FILE
                )
            )

        else:

            # Create empty files if no valid review date exists
            save_comma_separated_stock_list(
                [],
                BULLISH_LATEST_TXT_FILE
            )

            save_comma_separated_stock_list(
                [],
                BEARISH_LATEST_TXT_FILE
            )

    else:

        # Create empty files if there are no active snapshots
        save_comma_separated_stock_list(
            [],
            BULLISH_LATEST_TXT_FILE
        )

        save_comma_separated_stock_list(
            [],
            BEARISH_LATEST_TXT_FILE
        )


    print(
        "\n" + "=" * 100
    )
    print(
        "LATEST REVIEW-DATE TXT STOCK LISTS"
    )
    print(
        "=" * 100
    )

    if latest_review_for_txt is not None:

        print(
            f"\nLatest Review Date : "
            f"{latest_review_for_txt.date()}"
        )

        print(
            f"Bullish Stocks     : "
            f"{bullish_latest_count}"
        )

        print(
            f"Bearish Stocks     : "
            f"{bearish_latest_count}"
        )

    else:

        print(
            "\nNo valid active review snapshot was available."
        )


    # ========================================================
    # PERFORMANCE SUMMARY
    # ========================================================

    print("\n")
    print("=" * 100)
    print("BACKTEST COMPLETE")
    print("=" * 100)


    # --------------------------------------------------------
    # BULLISH
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("BULLISH PERFORMANCE")
    print("=" * 60)


    print(
        f"Completed Trades : "
        f"{len(bullish_trade_df)}"
    )


    if not bullish_trade_df.empty:

        bullish_wins = (
            bullish_trade_df[
                "Stock_Return_%"
            ] > 0
        ).sum()


        bullish_win_rate = (
            bullish_wins
            / len(
                bullish_trade_df
            )
        ) * 100


        print(
            f"Winning Trades   : "
            f"{bullish_wins}"
        )

        print(
            f"Win Rate         : "
            f"{bullish_win_rate:.2f}%"
        )

        print(
            f"Average Return   : "
            f"{bullish_trade_df['Stock_Return_%'].mean():.2f}%"
        )

        print(
            f"Median Return    : "
            f"{bullish_trade_df['Stock_Return_%'].median():.2f}%"
        )


        if (
            "Entry_Market_Regime"
            in bullish_trade_df.columns
        ):

            print(
                "\nBullish Trades by "
                "ENTRY Market Regime:"
            )

            regime = (
                bullish_trade_df
                .groupby(
                    "Entry_Market_Regime"
                )
                .agg(
                    Trades=(
                        "Stock",
                        "count"
                    ),

                    Average_Return=(
                        "Stock_Return_%",
                        "mean"
                    ),

                    Median_Return=(
                        "Stock_Return_%",
                        "median"
                    ),

                    Win_Rate=(
                        "Stock_Return_%",
                        lambda x:
                        (
                            (x > 0).mean()
                            * 100
                        )
                    )
                )
                .round(2)
            )

            print(
                regime.to_string()
            )


    print(
        f"\nStill Active Bullish : "
        f"{len(bullish_active)}"
    )


    # --------------------------------------------------------
    # BEARISH
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("BEARISH PERFORMANCE")
    print("=" * 60)


    print(
        f"Completed Trades : "
        f"{len(bearish_trade_df)}"
    )


    if not bearish_trade_df.empty:

        bearish_wins = (
            bearish_trade_df[
                "Stock_Return_%"
            ] > 0
        ).sum()


        bearish_win_rate = (
            bearish_wins
            / len(
                bearish_trade_df
            )
        ) * 100


        print(
            f"Winning Trades   : "
            f"{bearish_wins}"
        )

        print(
            f"Win Rate         : "
            f"{bearish_win_rate:.2f}%"
        )

        print(
            f"Average Return   : "
            f"{bearish_trade_df['Stock_Return_%'].mean():.2f}%"
        )

        print(
            f"Median Return    : "
            f"{bearish_trade_df['Stock_Return_%'].median():.2f}%"
        )


        if (
            "Entry_Market_Regime"
            in bearish_trade_df.columns
        ):

            print(
                "\nBearish Trades by "
                "ENTRY Market Regime:"
            )

            regime = (
                bearish_trade_df
                .groupby(
                    "Entry_Market_Regime"
                )
                .agg(
                    Trades=(
                        "Stock",
                        "count"
                    ),

                    Average_Return=(
                        "Stock_Return_%",
                        "mean"
                    ),

                    Median_Return=(
                        "Stock_Return_%",
                        "median"
                    ),

                    Win_Rate=(
                        "Stock_Return_%",
                        lambda x:
                        (
                            (x > 0).mean()
                            * 100
                        )
                    )
                )
                .round(2)
            )

            print(
                regime.to_string()
            )


    print(
        f"\nStill Active Bearish : "
        f"{len(bearish_active)}"
    )


    # ========================================================
    # OUTPUT FILES
    # ========================================================

    print("\n")
    print("=" * 100)
    print("FILES CREATED")
    print("=" * 100)

    print(
        f"\n1. Bullish completed trades:\n"
        f"{BULLISH_TRADE_FILE}"
    )

    print(
        f"\n2. Bearish completed trades:\n"
        f"{BEARISH_TRADE_FILE}"
    )

    print(
        f"\n3. Bullish entries/exits:\n"
        f"{BULLISH_CHANGES_FILE}"
    )

    print(
        f"\n4. Bearish entries/exits:\n"
        f"{BEARISH_CHANGES_FILE}"
    )

    print(
        f"\n5. Bullish full review history:\n"
        f"{BULLISH_REVIEW_FILE}"
    )

    print(
        f"\n6. Bearish full review history:\n"
        f"{BEARISH_REVIEW_FILE}"
    )

    print(
        f"\n7. Combined review history:\n"
        f"{COMBINED_REVIEW_FILE}"
    )

    print(
        f"\n8. Active stocks on every review:\n"
        f"{ACTIVE_SNAPSHOT_FILE}"
    )

    print(
        f"\n9. Current Bullish Backtest List:\n"
        f"{BULLISH_CURRENT_ACTIVE_FILE}"
    )

    print(
        f"\n10. Current Bearish Backtest List:\n"
        f"{BEARISH_CURRENT_ACTIVE_FILE}"
    )

    print(
        f"\n11. CRSLDX Market Regime History:\n"
        f"{MARKET_REGIME_FILE}"
    )

    print(
        f"\n12. Latest Review Bullish TXT List:\n"
        f"{BULLISH_LATEST_TXT_FILE}"
    )

    print(
        f"\n13. Latest Review Bearish TXT List:\n"
        f"{BEARISH_LATEST_TXT_FILE}"
    )


# ============================================================
#                       RUN
# ============================================================

if __name__ == "__main__":
    main()