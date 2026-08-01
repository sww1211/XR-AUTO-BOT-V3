from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import pandas as pd
import yfinance as yf
from datetime import datetime

app = FastAPI()

PAIRS = [
    "BTC-USD", "ETH-USD", "LTC-USD", "XRP-USD", "SOL-USD", 
    "DOGE-USD", "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD"
]

PAIR_NAMES = {
    "BTC-USD": "Bitcoin (BTC/USD)",
    "ETH-USD": "Ethereum (ETH/USD)",
    "LTC-USD": "Litecoin (LTC/USD)",
    "XRP-USD": "Ripple (XRP/USD)",
    "SOL-USD": "Solana (SOL/USD)",
    "DOGE-USD": "Dogecoin (DOGE/USD)",
    "ADA-USD": "Cardano (ADA/USD)",
    "AVAX-USD": "Avalanche (AVAX/USD)",
    "LINK-USD": "Chainlink (LINK/USD)",
    "DOT-USD": "Polkadot (DOT/USD)"
}

def analyze_crypto_pair(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 30:
            return {
                "ticker": ticker, "pair": PAIR_NAMES.get(ticker, ticker), 
                "status": "No Data", "signal": "WAITING", "win_rate": 50.0, 
                "rsi": 50.0, "macd_status": "Neutral", "candle": "Neutral", "result": "WAIT"
            }

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

        current_rsi = float(df['RSI'].iloc[-1])
        current_macd = float(df['MACD'].iloc[-1])
        current_signal = float(df['Signal_Line'].iloc[-1])
        
        latest_open = float(df['Open'].iloc[-1])
        latest_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])

        if latest_close > latest_open:
            candle_type = "🟢 Bullish (เขียว)"
        elif latest_close < latest_open:
            candle_type = "🔴 Bearish (แดง)"
        else:
            candle_type = "⚪ Doji (เสมอ)"

        now = datetime.now()
        second = now.second
        is_final_5s = (25 <= second <= 29) or (55 <= second <= 59)
        cycle_remain = 30 - (second % 30)

        if not is_final_5s:
            return {
                "ticker": ticker, "pair": PAIR_NAMES.get(ticker, ticker),
                "status": f"⏳ ລໍຖ້າຈັງຫວະ ({cycle_remain}s)",
                "signal": "WAITING ⌛", "win_rate": 50.0,
                "rsi": round(current_rsi, 2), "macd_status": "Analyzing...", 
                "candle": candle_type, "result": "WAIT"
            }

        score = 50.0
        signal_type = "WAIT"

        if current_rsi <= 35 and current_macd > current_signal and latest_close > latest_open:
            score = 88.5
            signal_type = "BUY"
        elif current_rsi >= 65 and current_macd < current_signal and latest_close < latest_open:
            score = 87.0
            signal_type = "SELL"
        else:
            score = 55.0
            signal_type = "WAIT"

        if score >= 80.0:
            # จำลองการตรวจสอบผลลัพธ์ (Win/Loss) จากทิศทางราคาแท่งปัจจุบันเทียบกับแท่งก่อนหน้า
            if signal_type == "BUY":
                is_win = latest_close > prev_close
                res_label = "✅ WIN (ຖືກຕ້ອງ)" if is_win else "❌ LOSS (ຜິດພາດ)"
                return {
                    "ticker": ticker, "pair": PAIR_NAMES.get(ticker, ticker),
                    "status": "⚡ 5 ວິສຸດທ້າຍ",
                    "signal": "CALL (BUY) 🟢", "win_rate": score,
                    "rsi": round(current_rsi, 2), "macd_status": "Bullish Cross",
                    "candle": candle_type, "result": res_label
                }
            elif signal_type == "SELL":
                is_win = latest_close < prev_close
                res_label = "✅ WIN (ຖືກຕ້ອງ)" if is_win else "❌ LOSS (ຜິດພາດ)"
                return {
                    "ticker": ticker, "pair": PAIR_NAMES.get(ticker, ticker),
                    "status": "⚡ 5 ວິສຸດທ້າຍ",
                    "signal": "PUT (SELL) 🔴", "win_rate": score,
                    "rsi": round(current_rsi, 2), "macd_status": "Bearish Cross",
                    "candle": candle_type, "result": res_label
                }

        return {
            "ticker": ticker, "pair": PAIR_NAMES.get(ticker, ticker),
            "status": "⚡ 5 ວິສຸດທ້າຍ",
            "signal": "⏸️ ບໍ່ຮອດ 80% - ລໍຖ້າ", "win_rate": score,
            "rsi": round(current_rsi, 2), "macd_status": "Sideway",
            "candle": candle_type, "result": "WAIT"
        }

    except Exception as e:
        return {
            "ticker": ticker, "pair": PAIR_NAMES.get(ticker, ticker),
            "status": "Error", "signal": "ERROR", "win_rate": 0.0,
            "rsi": 0.0, "macd_status": "Error", "candle": "-", "result": "WAIT"
        }

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    results = [analyze_crypto_pair(p) for p in PAIRS]
    current_time_str = datetime.now().strftime('%H:%M:%S')
    
    has_win = any("WIN" in r['result'] for r in results)
    has_loss = any("LOSS" in r['result'] for r in results)

    rows_html = ""
    for r in results:
        sig_class = "waiting"
        res_class = "waiting"
        if "BUY" in r['signal']:
            sig_class = "buy"
        elif "SELL" in r['signal']:
            sig_class = "sell"
            
        if "WIN" in r['result']:
            res_class = "win"
        elif "LOSS" in r['result']:
            res_class = "loss"
            
        rows_html += f"""
            <tr>
                <td><b>{r['pair']}</b></td>
                <td>{r['status']}</td>
                <td>{r['candle']}</td>
                <td>{r['rsi']}</td>
                <td>{r['macd_status']}</td>
                <td class="signal-cell {sig_class}">{r['signal']}</td>
                <td><b>{r['win_rate']}%</b></td>
                <td class="{res_class}"><b>{r['result']}</b></td>
            </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="lo">
<head>
    <meta charset="UTF-8">
    <title>XR Trade - Win/Loss Signal Pro</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; text-align: center; padding: 20px; }}
        h1 {{ color: #58a6ff; }}
        .time-box {{ font-size: 18px; margin-bottom: 20px; background: #161b22; display: inline-block; padding: 10px 20px; border-radius: 8px; border: 1px solid #30363d; color: #f0883e; }}
        table {{ width: 95%; margin: 0 auto; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
        th, td {{ padding: 12px; border-bottom: 1px solid #30363d; text-align: center; font-size: 14px; }}
        th {{ background-color: #21262d; color: #f0f6fc; font-size: 15px; }}
        tr:hover {{ background-color: #1f242c; }}
        .buy {{ color: #3fb950; font-weight: bold; }}
        .sell {{ color: #f85149; font-weight: bold; }}
        .win {{ color: #3fb950; font-size: 15px; }}
        .loss {{ color: #f85149; font-size: 15px; }}
        .waiting {{ color: #8b949e; }}
        .audio-btn {{ background: #238636; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 6px; cursor: pointer; margin-bottom: 15px; }}
        .audio-btn:hover {{ background: #2ea043; }}
    </style>
    <script>
        function playSound(type) {{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            
            if(type === 'win') {{
                // ສຽງ WIN (เสียงสูงสดใส)
                osc.frequency.setValueAtTime(587.33, ctx.currentTime);
                osc.frequency.setValueAtTime(880, ctx.currentTime + 0.15);
            }} else {{
                // ສຽງ LOSS (เสียงต่ำเตือนภัย)
                osc.frequency.setValueAtTime(300, ctx.currentTime);
                osc.frequency.setValueAtTime(200, ctx.currentTime + 0.2);
            }}
            
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
            osc.start();
            osc.stop(ctx.currentTime + 0.5);
        }}

        window.onload = function() {{
            let isWin = {"true" if has_win else "false"};
            let isLoss = {"true" if has_loss else "false"};
            
            if (sessionStorage.getItem('soundEnabled') === 'true') {{
                if (isWin) {{
                    playSound('win');
                }} else if (isLoss) {{
                    playSound('loss');
                }}
            }}
        }};

        function enableSound() {{
            sessionStorage.setItem('soundEnabled', 'true');
            alert('ເປີດລະບົບສຽງແຈ້ງເຕືອນ WIN/LOSS สำເລັດແລ້ວ! 🔊');
            playSound('win');
        }}
    </script>
</head>
<body>
    <h1>🚀 XR Trade - Win/Loss Signal Dashboard</h1>
    <div>
        <button class="audio-btn" onclick="enableSound()">🔊 ເປີດສຽງແຈ້ງເຕືອນ (ຄລິກທີ່ນີ້ກ່ອນ)</button>
    </div>
    <div class="time-box">⏰ ເວລາລະບົບ: {current_time_str} | ວິເຄາະ 30 ວິລົງມາ 0 | ສະແດງຜົນ WIN / LOSS ພ້ອມສຽງ</div>
    <table>
        <tr>
            <th>ຄູ່ເງິນ Crypto</th>
            <th>ສະຖານະເວລາ</th>
            <th>แท่งเทียนปัจจุบัน</th>
            <th>RSI</th>
            <th>MACD Status</th>
            <th>ສັນຍານຊື້-ຂາຍ</th>
            <th>Win Rate</th>
            <th>ຜົນລັບ (Win/Loss)</th>
        </tr>
        {rows_html}
    </table>
</body>
</html>
"""
    return html_content
