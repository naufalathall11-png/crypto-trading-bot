# Crypto Bot Starter V2 — Windows beginner edition

V2 menambahkan backtesting historis. Bot live tetap **tidak mengirim order sungguhan**.
Default: Indodax BTC/IDR, spot, timeframe 1 jam.

## A. Install Python di Windows
1. Buka https://www.python.org/downloads/windows/
2. Unduh Python 3.12 (64-bit) atau versi stabil terbaru yang kompatibel.
3. Jalankan installer. Centang **Add python.exe to PATH** sebelum klik Install Now.
4. Buka Command Prompt (tekan Windows, ketik `cmd`).
5. Jalankan `py --version`. Pastikan versi Python muncul.

Jika `py` tidak dikenali, tutup dan buka Command Prompt lagi. Jika masih gagal, ulangi instalasi dan pastikan PATH dicentang.

## B. Siapkan project
1. Extract `crypto_bot_v2.zip` ke folder yang mudah ditemukan, misalnya Desktop.
2. Buka folder `crypto_bot_v2`.
3. Klik address bar File Explorer, ketik `cmd`, lalu Enter. Command Prompt akan terbuka di folder itu.
4. Jalankan perintah berikut satu per satu:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

Jika berhasil, biasanya muncul `(.venv)` di awal baris Command Prompt.

## C. Jalankan backtest V2
```bat
py backtest.py
```
Contoh pair/timeframe lain:
```bat
py backtest.py --symbol ETH/IDR --timeframe 1h --limit 1000 --capital 1000000
```
Backtest mengambil data publik dari exchange melalui internet. Hasil dipengaruhi fee dan slippage asumsi. File `backtest_trades.csv` berisi trade yang selesai.

## D. Jalankan paper trading
```bat
py main.py
```
Hentikan dengan `Ctrl + C`. Catatan transaksi simulasi tersimpan di `paper_trades.csv`.

## E. Aturan dan batasan
- Paper trading saja. Tidak ada API key dan tidak ada order live.
- Strategi contoh: EMA50/EMA200, RSI, MACD; risiko simulasi 1%, stop loss 2%, target 4%.
- Backtest memakai entry di open candle berikutnya setelah sinyal candle tertutup. Untuk candle yang menyentuh stop dan target bersamaan, asumsi konservatifnya stop lebih dulu.
- Data OHLCV exchange publik bisa terbatas; contoh ini hanya meminta sampai 1000 candle.
- Hasil historis tidak menjamin hasil masa depan. Uji di berbagai periode, hitung fee aktual, slippage, spread, dan risiko.
- Jangan pernah membagikan API key/secret. Jangan aktifkan withdrawal pada API key.
- Jangan pindah ke uang sungguhan sebelum backtest, paper trading beberapa minggu, dan review risiko.

## Troubleshooting singkat
- `py is not recognized`: install ulang Python dengan opsi Add to PATH.
- `No module named ccxt/pandas`: aktifkan `.venv`, lalu `py -m pip install -r requirements.txt`.
- `Pair not found`: exchange mungkin memakai simbol berbeda; cek market yang tersedia di situs exchange.
- `Network/timeout`: periksa internet dan coba lagi nanti.
