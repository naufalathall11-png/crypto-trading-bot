"""Paper-trading crypto bot. No real orders are ever sent."""
import csv, os, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import ccxt
import pandas as pd

EXCHANGE_ID = os.getenv("EXCHANGE_ID", "indodax")
SYMBOL = os.getenv("SYMBOL", "BTC/IDR")
TIMEFRAME = os.getenv("TIMEFRAME", "1h")
STARTING_IDR = float(os.getenv("STARTING_IDR", "1000000"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.01"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.02"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.04"))
FEE_RATE = float(os.getenv("FEE_RATE", "0.003"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "300"))
LOG_FILE = Path("paper_trades.csv")

@dataclass
class Position:
    amount: float
    entry: float
    stop: float
    target: float
    entry_fee: float

def indicators(df):
    c = df["close"]
    df["ema50"] = c.ewm(span=50, adjust=False).mean()
    df["ema200"] = c.ewm(span=200, adjust=False).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["rsi"] = 100 - 100 / (1 + rs)
    df.loc[loss == 0, "rsi"] = 100
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    return df

def log_trade(action, price, amount, cash, note):
    fresh = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if fresh:
            w.writerow(["utc_time","action","price","amount","cash_idr","note"])
        w.writerow([datetime.now(timezone.utc).isoformat(), action, price, amount, cash, note])

def main():
    ex = getattr(ccxt, EXCHANGE_ID)({"enableRateLimit": True})
    ex.load_markets()
    if SYMBOL not in ex.markets:
        raise SystemExit(f"Pair {SYMBOL} tidak tersedia di {EXCHANGE_ID}. Periksa pair yang tersedia.")
    if not ex.has.get("fetchOHLCV"):
        raise SystemExit("Exchange tidak mendukung OHLCV melalui CCXT.")
    cash, pos, last_candle = STARTING_IDR, None, None
    print(f"PAPER TRADING | {EXCHANGE_ID} | {SYMBOL} | {TIMEFRAME}")
    print(f"Modal simulasi Rp{cash:,.0f}. Tidak ada order real.")

    while True:
        try:
            raw = ex.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=300)
            if len(raw) < 220:
                print("Data candle belum cukup."); time.sleep(POLL_SECONDS); continue
            df = indicators(pd.DataFrame(raw, columns=["timestamp","open","high","low","close","volume"]))
            r = df.iloc[-2]  # only completed candle
            candle = int(r.timestamp)
            if candle == last_candle:
                time.sleep(POLL_SECONDS); continue
            last_candle = candle
            price = float(r.close)
            buy = r.ema50 > r.ema200 and 50 < r.rsi < 70 and r.macd > r.macd_signal
            sell = r.ema50 < r.ema200 or r.rsi >= 75 or r.macd < r.macd_signal

            print(f"{datetime.fromtimestamp(candle/1000, timezone.utc)} close={price:.2f} RSI={r.rsi:.1f}")
            if pos is None and buy:
                risk_budget = cash * RISK_PER_TRADE
                stop = price * (1 - STOP_LOSS_PCT)
                qty = min(risk_budget / (price-stop), cash / (price * (1+FEE_RATE)))
                if qty > 0:
                    cost, fee = qty*price, qty*price*FEE_RATE
                    cash -= cost + fee
                    pos = Position(qty, price, stop, price*(1+TAKE_PROFIT_PCT), fee)
                    log_trade("PAPER_BUY", price, qty, cash, "strategy signal")
                    print(f"SIMULASI BUY qty={qty:.8f} @ {price:.2f}")
            elif pos:
                reason = "stop loss" if price <= pos.stop else "take profit" if price >= pos.target else "strategy exit" if sell else None
                if reason:
                    gross = pos.amount*price
                    fee = gross*FEE_RATE
                    cash += gross-fee
                    pnl = (price-pos.entry)*pos.amount-fee-pos.entry_fee
                    log_trade("PAPER_SELL", price, pos.amount, cash, f"{reason}; pnl={pnl:.2f}")
                    print(f"SIMULASI SELL: {reason}; P/L setelah fee sekitar Rp{pnl:,.0f}")
                    pos = None
            equity = cash + (pos.amount*price if pos else 0)
            print(f"Kas Rp{cash:,.0f} | Ekuitas Rp{equity:,.0f}")
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print("\nBot dihentikan. Tidak ada order real."); break
        except Exception as e:
            print(f"Error: {e}. Mencoba lagi nanti."); time.sleep(max(POLL_SECONDS,60))

if __name__ == "__main__":
    main()
