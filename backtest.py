"""Historical backtest for the starter strategy. No live orders."""
import argparse
import ccxt
import pandas as pd

def add_indicators(df):
    c = df.close
    df["ema50"] = c.ewm(span=50, adjust=False).mean()
    df["ema200"] = c.ewm(span=200, adjust=False).mean()
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    down = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = up / down.replace(0, float("nan"))
    df["rsi"] = 100 - 100/(1+rs)
    df.loc[down == 0, "rsi"] = 100
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    df["macd"] = macd
    df["macd_signal"] = macd.ewm(span=9, adjust=False).mean()
    return df

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exchange", default="indodax")
    p.add_argument("--symbol", default="BTC/IDR")
    p.add_argument("--timeframe", default="1h")
    p.add_argument("--limit", type=int, default=1000)
    p.add_argument("--capital", type=float, default=1_000_000)
    p.add_argument("--fee", type=float, default=0.003, help="Fee asumsi per sisi, misalnya 0.003 = 0.3%")
    p.add_argument("--slippage", type=float, default=0.001, help="Slippage asumsi per sisi, misalnya 0.001 = 0.1%")
    args = p.parse_args()

    ex = getattr(ccxt, args.exchange)({"enableRateLimit": True})
    ex.load_markets()
    if args.symbol not in ex.markets:
        raise SystemExit(f"Pair {args.symbol} tidak ditemukan di {args.exchange}.")
    rows = ex.fetch_ohlcv(args.symbol, args.timeframe, limit=min(args.limit, 1000))
    if len(rows) < 250:
        raise SystemExit("Data kurang dari 250 candle. Coba pair/timeframe lain.")
    df = add_indicators(pd.DataFrame(rows, columns=["timestamp","open","high","low","close","volume"]))
    df = df.reset_index(drop=True)

    cash, qty, entry, stop, target, entry_cost = args.capital, 0.0, None, None, None, 0.0
    trades, wins, equity_curve = [], 0, []
    risk_fraction, sl_pct, tp_pct = 0.01, 0.02, 0.04

    # Signal from completed candle i; market entry/exit assumed at next candle open.
    # If stop and target both touched within one candle, conservative assumption: stop first.
    for i in range(201, len(df)-1):
        sig = df.iloc[i]
        nxt = df.iloc[i+1]
        if pd.isna(sig.rsi):
            continue
        open_next = float(nxt.open)
        if qty == 0:
            buy = sig.ema50 > sig.ema200 and 50 < sig.rsi < 70 and sig.macd > sig.macd_signal
            if buy:
                fill = open_next * (1 + args.slippage)
                stop_candidate = fill * (1-sl_pct)
                risk_cash = cash * risk_fraction
                amount = min(risk_cash/(fill-stop_candidate), cash/(fill*(1+args.fee)))
                if amount > 0:
                    entry_cost = amount*fill*args.fee
                    cash -= amount*fill + entry_cost
                    qty, entry = amount, fill
                    stop, target = fill*(1-sl_pct), fill*(1+tp_pct)
        else:
            low, high = float(nxt.low), float(nxt.high)
            reason, raw_fill = None, None
            if low <= stop:
                reason, raw_fill = "stop loss", stop
            elif high >= target:
                reason, raw_fill = "take profit", target
            elif sig.ema50 < sig.ema200 or sig.rsi >= 75 or sig.macd < sig.macd_signal:
                reason, raw_fill = "strategy exit", open_next
            if reason:
                fill = raw_fill * (1-args.slippage)
                gross = qty*fill
                fee = gross*args.fee
                cash += gross-fee
                pnl = (fill-entry)*qty - fee - entry_cost
                trades.append({"entry":entry,"exit":fill,"qty":qty,"pnl":pnl,"reason":reason})
                if pnl > 0: wins += 1
                qty, entry, stop, target, entry_cost = 0.0, None, None, None, 0.0
        mark = cash + qty*float(nxt.close)
        equity_curve.append(mark)

    last_price = float(df.iloc[-1].close)
    final_equity = cash + qty*last_price
    peak, max_dd = args.capital, 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak:
            max_dd = max(max_dd, (peak-value)/peak)
    total_return = (final_equity/args.capital-1)*100
    print("\n=== HASIL BACKTEST (SIMULASI, BUKAN PREDIKSI) ===")
    print(f"Exchange/pair       : {args.exchange} {args.symbol}")
    print(f"Timeframe           : {args.timeframe}")
    print(f"Candle dianalisis   : {len(df)}")
    print(f"Modal awal          : Rp{args.capital:,.0f}")
    print(f"Ekuitas akhir       : Rp{final_equity:,.0f} (posisi terbuka dinilai pada harga terakhir)")
    print(f"Return              : {total_return:.2f}%")
    print(f"Jumlah trade selesai: {len(trades)}")
    print(f"Win rate            : {(wins/len(trades)*100 if trades else 0):.2f}%")
    print(f"Max drawdown*       : {max_dd*100:.2f}%")
    print(f"Asumsi fee/sisi     : {args.fee*100:.3f}%")
    print(f"Asumsi slippage/sisi: {args.slippage*100:.3f}%")
    print("*Max drawdown dihitung dari kurva ekuitas sampel; hasil terbatas oleh data historis yang tersedia.")
    if trades:
        pd.DataFrame(trades).to_csv("backtest_trades.csv", index=False)
        print("Detail trade tersimpan di backtest_trades.csv")

if __name__ == "__main__":
    main()
