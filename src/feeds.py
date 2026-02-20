import asyncio
import aiohttp
import time
import logging

import config

logger = logging.getLogger(__name__)

BINANCE_API = "https://api.binance.com/api/v3"


class State:
    def __init__(self):
        self.bids: list[tuple[float, float]] = []
        self.asks: list[tuple[float, float]] = []
        self.mid: float = 0.0

        self.trades: list[dict] = []

        self.klines: list[dict] = []
        self.cur_kline: dict | None = None

        self.pm_up_id: str | None = None
        self.pm_dn_id: str | None = None
        self.pm_up: float | None = None
        self.pm_dn: float | None = None


async def bootstrap(symbol: str, interval: str, state: State):
    url = f"{BINANCE_API}/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 500
    }

    print(f"[Binance bootstrap] symbol={symbol}, interval={interval}")
    print(f"Request → {url}")
    print(f"Parameters: {params}")

    start_time = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as resp:
                print(f"HTTP status: {resp.status}")

                if resp.status != 200:
                    text = await resp.text()
                    print(f"Binance returned error {resp.status}:\n{text[:600]}")
                    logger.error(f"Binance HTTP {resp.status}: {text[:300]}")
                    return

                try:
                    data = await resp.json()
                except Exception as e:
                    text = await resp.text()
                    print(f"JSON parse error: {e}")
                    print(f"Raw response (first 500 chars):\n{text[:500]}")
                    return

                elapsed = time.time() - start_time
                print(f"Received {len(data)} items in {elapsed:.2f} sec")

                if not isinstance(data, list):
                    print("Response is NOT a list → likely API error")
                    print("Received object:", data)
                    return

                if len(data) == 0:
                    print("Received empty list of candles")
                    return

                print("First candle:", data[0])
                print("Last candle:", data[-1])

                candles = []
                bad_candles = 0

                for r in data:
                    if not isinstance(r, list) or len(r) < 6:
                        print("Bad candle (not list or too short):", r)
                        bad_candles += 1
                        continue

                    try:
                        candle = {
                            "t": int(r[0]) / 1000.0,
                            "o": float(r[1]),
                            "h": float(r[2]),
                            "l": float(r[3]),
                            "c": float(r[4]),
                            "v": float(r[5]),
                        }
                        candles.append(candle)
                    except (ValueError, TypeError) as e:
                        print(f"Candle conversion error: {e} → {r}")
                        bad_candles += 1
                        continue

                print(f"Successfully processed {len(candles)} candles, skipped bad: {bad_candles}")

                if candles:
                    state.klines = candles
                    print(f"Candles saved to state.klines, count: {len(state.klines)}")
                    print(f"Last candle timestamp: {state.klines[-1]['t']}")

    except aiohttp.ClientError as e:
        print(f"Network error contacting Binance: {e}")
    except Exception as e:
        print(f"Unexpected error in bootstrap: {type(e).__name__}: {e}")


async def ob_poller(symbol: str, state: State):
    print(f"[Order Book poller] started for {symbol}")
    while True:
        await asyncio.sleep(3)


async def binance_feed(symbol: str, interval: str, state: State):
    print(f"[Binance websocket feed] {symbol} {interval}")
    while True:
        await asyncio.sleep(10)


async def pm_feed(state: State):
    print("[Polymarket feed] started")
    while True:
        await asyncio.sleep(5)


def fetch_pm_tokens(coin: str, tf: str):
    print(f"Fetching Polymarket tokens for {coin} {tf}")
    return "example_up_id", "example_down_id"