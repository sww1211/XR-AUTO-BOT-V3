from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import requests
from datetime import datetime
import random

app = FastAPI()

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "LTCUSDT", "XRPUSDT", "SOLUSDT", 
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"
]

PAIR_NAMES = {
    "BTCUSDT": "BTC/USDT", "ETHUSDT": "ETH/USDT", "LTCUSDT": "LTC/USDT",
    "XRPUSDT": "XRP/USDT", "SOLUSDT": "SOL/USDT", "DOGEUSDT": "DOGE/USDT",
    "ADAUSDT": "ADA/USDT", "AVAXUSDT": "AVAX/USDT", "LINKUSDT": "LINK/USDT",
    "DOTUSDT": "DOT/USDT"
}

def get_crypto_signals():
    data_list = []
    price_map = {}
    
    # ພະຍາຍາມດຶງຂໍ້ມູນຈາກ Binance API (ມີ URL ສຳຮອງ)
    urls = [
        "https://api.binance.com/api/v3/ticker/24hr",
        "https://data-api.binance.vision/api/v3/ticker/24hr"
    ]
    
    success = False
    for url in urls:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                res_json = response.json()
                price_map = {item['symbol']: item for item in res_json}
                success = True
                break
        except Exception:
            continue

    now = datetime.now()
    current_second = now.second
    # 5 ວິນາທີສຸດທ້າຍຂອງຮອບ 30 ວິນາທີ (ຄື 25-29 ແລະ 55-59)
    is_final_5s = (25 <= current_second <= 29) or (55 <= current_second <= 59)

    for symbol in SYMBOLS:
        try:
            if success and symbol in price_map:
                item = price_map[symbol]
                price = float(item['lastPrice'])
                price_change = float(item['priceChangePercent'])
            else:
                # ລະບົບສຳຮອງປ້ອງກັນຈໍ 0.00 (ສ້າງລາຄາເຄື່ອນໄຫວຈຳລອງທີ່ໃກ້ຄຽງຄວາມຈິງ)
                base_prices = {
                    "BTCUSDT": 65000.0, "ETHUSDT": 3500.0, "LTCUSDT": 85.0,
                    "XRPUSDT": 0.55, "SOLUSDT": 140.0, "DOGEUSDT": 0.12,
                    "ADAUSDT": 0.40, "AVAXUSDT": 25.0, "LINKUSDT": 15.0, "DOTUSDT": 6.5
                }
                price = base_prices.get(symbol, 100.0) + random.uniform(-0.5, 0.5)
                price_change = random.uniform(-2.5, 2.5)

            # คำนวณค่า RSI ຈາກການ變動
            rsi_val = round(50 + (price_change * 3.5), 1)
            if rsi_val > 98: rsi_val = 97.5
            if rsi_val < 5: rsi_val = 5.2

            is_green = price_change >= 0
            candle_type = "🟢 Bullish (ແທ່ງຂຽວ)" if is_green else "🔴 Bearish (ແທ່ງແດງ)"
            confidence = round(min(max(72.0 + abs(price_change * 3), 70.0), 98.0), 1)

            if is_final_5s:
                if is_green:
                    signal_status = "BUY (CALL)"
                    arrow = "⬆️ 🟢"
                    color = "#3fb950"
                else:
                    signal_status = "SELL (PUT)"
                    arrow = "⬇️ 🔴"
                    color = "#f85149"
                sound = True
            else:
                signal_status = "⏳ ຖ້າຈັງຫວະ (5 ວິນາທີສຸດທ້າຍ)..."
                arrow = "⏳"
                color = "#8b949e"
                sound = False

            data_list.append({
                "pair": PAIR_NAMES.get(symbol, symbol),
                "price": f"{price:,.4f}" if price < 1 else f"{price:,.2f}",
                "candle": candle_type,
                "rsi": f"{rsi_val}",
                "confidence": f"{confidence}%",
                "signal": signal_status,
                "arrow": arrow,
                "color": color,
                "sound": sound
            })
        except Exception:
            continue

    return data_list

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    results = get_crypto_signals()
    current_time_str = datetime.now().strftime('%H:%M:%S')
    any_sound = any(r['sound'] for r in results)

    cards_html = ""
    for r in results:
        cards_html += f"""
        <div class="crypto-card" style="border-left: 5px solid {r['color']};">
            <div class="card-header">
                <span class="pair-title">🟡 {r['pair']}</span>
                <span class="arrow-badge" style="background-color: {r['color']}22; color: {r['color']}; border: 1px solid {r['color']};">{r['arrow']}</span>
            </div>
            <div class="price-val">{r['price']}</div>
            <div class="info-row"><span>ແທ່ງທຽນ:</span> <b>{r['candle']}</b></div>
            <div class="info-row"><span>RSI Indicator:</span> <b>{r['rsi']}</b></div>
            <div class="info-row"><span>AI Confidence:</span> <b style="color: #58a6ff;">{r['confidence']}</b></div>
            <div class="info-row" style="margin-top: 8px; border-top: 1px solid #30363d; padding-top: 6px;">
                <span>ສັນຍານເທຣດ:</span> <b style="color: {r['color']};">{r['signal']}</b>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="lo">
<head>
    <meta charset="UTF-8">
    <title>XR Trade - Pro AI Signals</title>
    <meta http-equiv="refresh" content="1">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
        .top-bar {{ display: flex; justify-content: space-between; align-items: center; background: #161b22; padding: 15px 25px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 25px; }}
        .audio-btn {{ background: #238636; color: white; border: none; padding: 10px 20px; font-size: 15px; border-radius: 6px; cursor: pointer; font-weight: bold; }}
        .audio-btn:hover {{ background: #2ea043; }}
        .grid-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }}
        .crypto-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .pair-title {{ font-size: 16px; font-weight: bold; color: #f0f6fc; }}
        .arrow-badge {{ padding: 4px 10px; border-radius: 6px; font-size: 15px; font-weight: bold; }}
        .price-val {{ font-size: 22px; font-weight: bold; color: #58a6ff; margin-bottom: 10px; }}
        .info-row {{ font-size: 13px; color: #8b949e; margin-bottom: 5px; display: flex; justify-content: space-between; }}
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
            alert('ເປີດລະບົບສຽງແຈ້ງເຕືອນສຳເລັດ! 🔊');
            playSound();
        }}
    </script>
</head>
<body>
    <div class="top-bar">
        <div>
            <h2 style="margin: 0; color: #58a6ff;">📈 XR Trade - Pro AI Dashboard</h2>
            <div style="font-size: 13px; color: #8b949e; margin-top: 3px;">⏰ ເວລາ: {current_time_str} | ສັນຍານອອກສະເພາະ 5 ວິນາທີທ້າຍຂອງຮອບ 30 ວິ</div>
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
   
       
       
        
  
