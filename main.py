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
                "pair": PAIR_NAMES.get(ticker, ticker), "price": "0.00",
                "status": "WAIT", "up_pct": 50.0, "down_pct": 50.0,
                "strength": "ອ່ອນ", "confidence": "50.0%", "score_up": "0", "score_down": "0",
                "market_conf": "50/100", "diff": "0.00%", "reasons": ["No Data"], "sound": False
            }

        # 1. คำนวณ RSI & MACD
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

        current_price = float(df['Close'].iloc[-1])
        current_rsi = float(df['RSI'].iloc[-1])
        current_macd = float(df['MACD'].iloc[-1])
        current_signal = float(df['Signal_Line'].iloc[-1])
        
        latest_open = float(df['Open'].iloc[-1])
        latest_close = float(df['Close'].iloc[-1])

        # คำนวณเปอร์เซັນต์ Up / Down จำลองจาก RSI และ MACD
        up_pct = round(min(max(float(current_rsi), 10.0), 90.0), 2)
        down_pct = round(100.0 - up_pct, 2)

        # 2. ระบบเวลา 30 วินาที
        now = datetime.now()
        second = now.second
        is_final_5s = (25 <= second <= 29) or (55 <= second <= 59)

        signal_status = "WAIT"
        strength = "ອ່ອນ"
        reasons = ["Neutral Candle", "Close = Mid", "Open = Mid"]
        sound = False

        if current_rsi <= 38 and current_macd > current_signal and latest_close > latest_open:
            signal_status = "BUY"
            strength = "ແຂງແກ່ນ"
            reasons = ["Bullish Candle", "Strong Bullish Body", "RSI Oversold Bounce"]
            if is_final_5s:
                sound = True
        elif current_rsi >= 62 and current_macd < current_signal and latest_close < latest_open:
            signal_status = "SELL"
            strength = "ແຂງແກ່ນ"
            reasons = ["Bearish Candle", "Strong Bearish Body", "RSI Overbought Drop"]
            if is_final_5s:
                sound = True

        return {
            "pair": PAIR_NAMES.get(ticker, ticker),
            "price": f"{current_price:,.4f}" if current_price < 1 else f"{current_price:,.2f}",
            "status": signal_status,
            "up_pct": up_pct,
            "down_pct": down_pct,
            "strength": strength,
            "confidence": f"{up_pct}%" if signal_status == "BUY" else f"{down_pct}%",
            "score_up": f"{round(current_rsi, 2)}",
            "score_down": f"{round(100 - current_rsi, 2)}",
            "market_conf": f"{int(up_pct)}/100",
            "diff": f"{round(abs(current_macd), 2)}%",
            "reasons": reasons,
            "sound": sound
        }

    except Exception as e:
        return {
            "pair": PAIR_NAMES.get(ticker, ticker), "price": "0.00",
            "status": "WAIT", "up_pct": 50.0, "down_pct": 50.0,
            "strength": "Error", "confidence": "0%", "score_up": "0", "score_down": "0",
            "market_conf": "0/100", "diff": "0%", "reasons": ["Error fetching data"], "sound": False
        }

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    results = [analyze_crypto_pair(p) for p in PAIRS]
    current_time_str = datetime.now().strftime('%H:%M:%S')
    any_sound = any(r['sound'] for r in results)

    cards_html = ""
    for r in results:
        status_bg = "#21262d"
        status_color = "#8b949e"
        if r['status'] == "BUY":
            status_bg = "#238636"
            status_color = "#ffffff"
        elif r['status'] == "SELL":
            status_bg = "#da3633"
            status_color = "#ffffff"

        reasons_html = "".join([f'<span class="reason-tag">{rs}</span>' for rs in r['reasons']])

        cards_html += f"""
        <div class="crypto-card">
            <div class="card-header">
                <span class="pair-title">🟡 {r['pair']}</span>
                <span class="status-badge" style="background-color: {status_bg}; color: {status_color};">{r['status']}</span>
            </div>
            
            <div class="price-section">
                <div class="price-label">ລາຄາປັດຈຸບັນ</div>
                <div class="price-value">{r['price']}</div>
            </div>

            <div class="pct-bar-container">
                <div class="pct-labels">
                    <span style="color: #3fb950;">UP {r['up_pct']}%</span>
                    <span style="color: #f85149;">DOWN {r['down_pct']}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill-up" style="width: {r['up_pct']}%;"></div>
                </div>
            </div>

            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric-title">ຄວາມແຂງແກ່ນ</div>
                    <div class="metric-val" style="color: {'#3fb950' if r['strength']=='ແຂງແກ່ນ' else '#8b949e'};">{r['strength']}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">ຄວາມໝັ້ນໃຈ</div>
                    <div class="metric-val">{r['confidence']}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">ຄະແນນຂາຂຶ້ນ</div>
                    <div class="metric-val">{r['score_up']}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">ຄະແນນຂາລົງ</div>
                    <div class="metric-val">{r['score_down']}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">ຄວາມເຊື່ອໝັ້ນຕະຫຼາດ</div>
                    <div class="metric-val">{r['market_conf']}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">ສ່ວນຕ່າງທິດທາງ</div>
                    <div class="metric-val">{r['diff']}</div>
                </div>
            </div>

            <div class="reasons-section">
                <div class="reasons-title">ເຫດຜົນການວິເຄາະ</div>
                <div class="reasons-flex">
                    {reasons_html}
                </div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="lo">
<head>
    <meta charset="UTF-8">
    <title>XR Trade - Pro Card Dashboard</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
        .top-bar {{ display: flex; justify-content: space-between; align-items: center; background: #161b22; padding: 15px 25px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 25px; }}
        .audio-btn {{ background: #238636; color: white; border: none; padding: 10px 20px; font-size: 15px; border-radius: 6px; cursor: pointer; font-weight: bold; }}
        .audio-btn:hover {{ background: #2ea043; }}
        .grid-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }}
        .crypto-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .pair-title {{ font-size: 18px; font-weight: bold; color: #f0f6fc; }}
        .status-badge {{ padding: 4px 12px; border-radius: 6px; font-size: 13px; font-weight: bold; }}
        .price-section {{ background: #0d1117; padding: 10px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #21262d; }}
        .price-label {{ font-size: 12px; color: #8b949e; }}
        .price-value {{ font-size: 20px; font-weight: bold; color: #58a6ff; }}
        .pct-bar-container {{ margin-bottom: 15px; }}
        .pct-labels {{ display: flex; justify-content: space-between; font-size: 12px; font-weight: bold; margin-bottom: 5px; }}
        .progress-bar {{ background: #f85149; height: 6px; border-radius: 3px; overflow: hidden; }}
        .progress-fill-up {{ background: #3fb950; height: 100%; }}
        .metrics-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 15px; }}
        .metric-box {{ background: #0d1117; padding: 8px; border-radius: 6px; border: 1px solid #21262d; }}
        .metric-title {{ font-size: 11px; color: #8b949e; }}
        .metric-val {{ font-size: 13px; font-weight: bold; color: #f0f6fc; margin-top: 2px; }}
        .reasons-title {{ font-size: 12px; color: #8b949e; margin-bottom: 6px; }}
        .reasons-flex {{ display: flex; flex-wrap: wrap; gap: 5px; }}
        .reason-tag {{ background: #21262d; color: #c9d1d9; font-size: 11px; padding: 4px 8px; border-radius: 4px; border: 1px solid #30363d; }}
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
    <div class="top-bar">
        <div>
            <h2 style="margin: 0; color: #58a6ff;">🚀 XR Trade - Pro Signal Dashboard</h2>
            <div style="font-size: 13px; color: #8b949e; margin-top: 3px;">⏰ ເวລາລະບົບ: {current_time_str} | ອັບເດດແບບ Real-time</div>
        </div>
        <div>
            <button class="audio-btn" onclick="enableSound()">🔊 ເປີດສຽງແຈ້ງເຕືອນ</button>
        </div>
    </div>

    <div class="grid-container">
        {cards_html}
    </div>
</body>
</html>
"""
    return html_content
   
       
       
        
  
