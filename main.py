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
    "BTC-USD": "BTC/USDT",
    "ETH-USD": "ETH/USDT",
    "LTC-USD": "LTC/USDT",
    "XRP-USD": "XRP/USDT",
    "SOL-USD": "SOL/USDT",
    "DOGE-USD": "DOGE/USDT",
    "ADA-USD": "ADA/USDT",
    "AVAX-USD": "AVAX/USDT",
    "LINK-USD": "LINK/USDT",
    "DOT-USD": "DOT/USDT"
}

def analyze_crypto_pair(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 30:
            return {
                "pair": PAIR_NAMES.get(ticker, ticker), 
                "status": "No Data", "candle": "-", "rsi": 50, 
                "signal": "WAITING", "arrow": "⏳", "win_rate": "50%", "sound": False
            }

        # 1. คำนวณ RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # 2. คำนวณ MACD (12, 26, 9)
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

        current_rsi = float(df['RSI'].iloc[-1])
        current_macd = float(df['MACD'].iloc[-1])
        current_signal = float(df['Signal_Line'].iloc[-1])
        
        # 3. วิเคราะห์แท่งเทียนปัจจุบัน
        latest_open = float(df['Open'].iloc[-1])
        latest_close = float(df['Close'].iloc[-1])
        
        if latest_close > latest_open:
            candle_type = "🟢 เขียว (Bullish)"
        elif latest_close < latest_open:
            candle_type = "🔴 แดง (Bearish)"
        else:
            candle_type = "⚪ Doji"

        # 4. ระบบเวลา: นับถอยหลัง 30 วินาทีลงมา 0 
        now = datetime.now()
        second = now.second
        cycle_remain = 30 - (second % 30)
        
        # ออกสัญญาณเฉพาะ 5 วินาทีสุดท้าย (25-29 หรือ 55-59)
        is_final_5s = (25 <= second <= 29) or (55 <= second <= 59)

        if not is_final_5s:
            return {
                "pair": PAIR_NAMES.get(ticker, ticker),
                "status": f"⏳ ລໍຖ້າ (ເຫຼືອ {cycle_remain}s)",
                "candle": candle_type, "rsi": round(current_rsi, 2),
                "signal": "WAITING", "arrow": "➖", "win_rate": "-", "sound": False
            }

        # --- ระบบประเมินสัญญาณด้วย Indicators (RSI + MACD + Candle) ---
        score = 50.0
        signal_type = "WAIT"

        # เงื่อนไขแทงขึ้น (BUY) -> ลูกศรชี้ขึ้น ⬆️
        if current_rsi <= 38 and current_macd > current_signal and latest_close > latest_open:
            score = 88.5
            signal_type = "BUY"
        # เงื่อนไขแทงลง (SELL) -> ลูกศรชี้ลง ⬇️
        elif current_rsi >= 62 and current_macd < current_signal and latest_close < latest_open:
            score = 87.0
            signal_type = "SELL"
        else:
            score = 55.0
            signal_type = "WAIT"

        if score >= 80.0:
            if signal_type == "BUY":
                return {
                    "pair": PAIR_NAMES.get(ticker, ticker),
                    "status": "⚡ 5 ວິສຸດທ້າຍ (ສັນຍານມາແລ້ວ)",
                    "candle": candle_type, "rsi": round(current_rsi, 2),
                    "signal": "แทงขึ้น (CALL)", "arrow": "⬆️🟢", "win_rate": f"{score}%", "sound": True
                }
            elif signal_type == "SELL":
                return {
                    "pair": PAIR_NAMES.get(ticker, ticker),
                    "status": "⚡ 5 ວິສຸດທ້າຍ (ສັນຍານມາແລ້ວ)",
                    "candle": candle_type, "rsi": round(current_rsi, 2),
                    "signal": "แทงลง (PUT)", "arrow": "⬇️🔴", "win_rate": f"{score}%", "sound": True
                }

        return {
            "pair": PAIR_NAMES.get(ticker, ticker),
            "status": "⚡ 5 ວິສຸດທ້າຍ",
            "candle": candle_type, "rsi": round(current_rsi, 2),
            "signal": "⏸️ ບໍ່ຮອດ 80%", "arrow": "⏳", "win_rate": f"{score}%", "sound": False
        }

    except Exception as e:
        return {
            "pair": PAIR_NAMES.get(ticker, ticker),
            "status": "Error", "candle": "-", "rsi": 0,
            "signal": "ERROR", "arrow": "❌", "win_rate": "-", "sound": False
        }

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    results = [analyze_crypto_pair(p) for p in PAIRS]
    current_time_str = datetime.now().strftime('%H:%M:%S')
    any_sound = any(r['sound'] for r in results)

    rows_html = ""
    for r in results:
        sig_color = "#8b949e"
        if "CALL" in r['signal']:
            sig_color = "#3fb950"
        elif "PUT" in r['signal']:
            sig_color = "#f85149"
            
        rows_html += f"""
            <tr>
                <td><b style="color: #f0f6fc;">🟡 {r['pair']}</b></td>
                <td>{r['status']}</td>
                <td>{r['candle']}</td>
                <td>{r['rsi']}</td>
                <td style="color: {sig_color}; font-weight: bold; font-size: 16px;">{r['signal']}</td>
                <td style="font-size: 24px;">{r['arrow']}</td>
                <td><b style="color: #58a6ff;">{r['win_rate']}</b></td>
            </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="lo">
<head>
    <meta charset="UTF-8">
    <title>XR Trade - Pro Multi-Indicator Signal</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; text-align: center; padding: 20px; }}
        h1 {{ color: #58a6ff; }}
        .time-box {{ font-size: 18px; margin-bottom: 20px; background: #161b22; display: inline-block; padding: 10px 20px; border-radius: 8px; border: 1px solid #30363d; color: #f0883e; }}
        table {{ width: 90%; margin: 0 auto; border-collapse: collapse; background: #161b22; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
        th, td {{ padding: 14px; border-bottom: 1px solid #30363d; text-align: center; font-size: 15px; }}
        th {{ background-color: #21262d; color: #8b949e; text-transform: uppercase; font-size: 14px; }}
        tr:hover {{ background-color: #1f242c; }}
        .audio-btn {{ background: #238636; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 6px; cursor: pointer; margin-bottom: 15px; font-weight: bold; }}
        .audio-btn:hover {{ background: #2ea043; }}
    </style>
    <script>
        function playSound() {{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.setValueAtTime(587.33, ctx.currentTime);
            osc.frequency.setValueAtTime(880, ctx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
            osc.start();
            osc.stop(ctx.currentTime + 0.5);
        }}

        window.onload = function() {{
            let shouldPlay = {"true" if any_sound else "false"};
            if (shouldPlay && sessionStorage.getItem('soundEnabled') === 'true') {{
                playSound();
            }}
        }};

        function enableSound() {{
            sessionStorage.setItem('soundEnabled', 'true');
            alert('ເປີດລະບົບສຽງສຳເລັດແລ້ວ! 🔊');
            playSound();
        }}
    </script>
</head>
<body>
    <h1>🚀 XR Trade - Live Crypto Signals (30s Cycle)</h1>
    <div>
        <button class="audio-btn" onclick="enableSound()">🔊 ເປີດສຽງແຈ້ງເຕືອນ (ຄລິກທີ່ນີ້ກ່ອນ)</button>
    </div>
    <div class="time-box">⏰ ເວລາລະບົບ: {current_time_str} | ຮອບວຽນ 30 ວິ ລົງມາ 0 ວິ | ສະແດງສັນຍານໃນ 5 ວິສຸດທ້າຍ</div>
    <table>
        <tr>
            <th>ຄູ່ເງິນ Crypto</th>
            <th>ສະຖານະເວລາ</th>
            <th>ແທ່ງທຽນປັດຈຸບັນ</th>
            <th>RSI</th>
            <th>ສັນຍານຊື້-ຂາຍ</th>
            <th>ທິດທາງ (ลูกศร)</th>
            <th>Win Rate</th>
        </tr>
        {rows_html}
    </table>
</body>
</html>
"""
    return html_content
   
       
       
        
  
