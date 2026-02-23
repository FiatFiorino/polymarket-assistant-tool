# Polymarket Crypto Assistant Tool

Real-time terminal dashboard that combines live Binance order flow with Polymarket prediction market prices to surface actionable crypto signals.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![GitHub stars](https://img.shields.io/github/stars/FiatFiorino/polymarket-assistant-tool?style=social)
![GitHub forks](https://img.shields.io/github/forks/FiatFiorino/polymarket-assistant-tool?style=social)

---

## Screenshots
![alt](screen1.png)
![alt](screen2.png)

---

## Quick Start

### Requirements

- Python **3.10 or higher** (recommended: 3.11 / 3.12)  
  → https://www.python.org/downloads/

### Installation

1. Clone the repository
```bash
   git clone https://github.com/FiatFiorino/polymarket-assistant-tool.git
   cd polymarket-assistant-tool
```
2. Install dependencies
```bash
pip install -r requirements.txt
```
3.Configure .env file (very important!)
```bash
cp .env.example .env
```
Open .env and fill in your values.

4. Run the tool
```bash
python main.py
```
---
## What it does

- Streams live trades and orderbook from **Binance**
- Fetches Up/Down contract prices from **Polymarket** via WebSocket
- Calculates 11 indicators across orderbook, flow, and technical analysis
- Aggregates everything into a single **BULLISH / BEARISH / NEUTRAL** trend score
- Renders the full dashboard in the terminal with live refresh
- Sends notifications to a Telegram bot about a trend change and about a strong bullish/bearish trend.
---

## Supported coins & timeframes

| Coins | Timeframes |
|-------|------------|
| BTC, ETH, SOL, XRP | 5m, 15m, 1h, 4h, daily |

All 16 coin × timeframe combinations are supported on Polymarket.

---

## Indicators

**Order Book**
- OBI (Order Book Imbalance)
- Buy / Sell Walls
- Liquidity Depth (0.1% / 0.5% / 1.0%)

**Flow & Volume**
- CVD (Cumulative Volume Delta) — 1m / 3m / 5m
- Delta (1m)
- Volume Profile with POC

**Technical Analysis**
- RSI (14)
- MACD (12/26/9) + Signal + Histogram
- VWAP
- EMA 5 / EMA 20 crossover
- Heikin Ashi candle streak

---

## Roadmap (planned features)

- [ ] Web version (Streamlit / Dash)
- [ ] Paper trading & real exchange integration
- [ ] Additional indicators: Bollinger Bands, Funding Rates, Liquidation data

---

## License

MIT License — see the LICENSE file.

