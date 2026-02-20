import sys
import os
import asyncio
from datetime import datetime

import rich

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.live import Live

import config
from src import feeds
import dashboard

from dotenv import load_dotenv
from telegram_notifier import send_strong_signal, send_trend_change, shutdown_notifier

load_dotenv()

console = Console(force_terminal=True)

TELEGRAM_ENABLED = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))

class DashboardState:
    def __init__(self):
        self.last_direction = {}
        self.last_strong_notify = {}
        self.last_change_notify = {}

    def should_notify_strong(self, symbol: str, tf: str):
        key = f"{symbol}_{tf}"
        now = asyncio.get_event_loop().time()
        last = self.last_strong_notify.get(key, 0)
        return now - last > int(os.getenv("ANTI_SPAM_STRONG_SEC", 180))

    def update_strong_notify(self, symbol: str, tf: str):
        key = f"{symbol}_{tf}"
        self.last_strong_notify[key] = asyncio.get_event_loop().time()

    def check_trend_change(self, symbol: str, tf: str, new_direction: str, score: float):
        key = f"{symbol}_{tf}"
        old = self.last_direction.get(key, "NEUTRAL")
        self.last_direction[key] = new_direction

        if old == new_direction:
            return None

        if new_direction == "NEUTRAL":
            return None

        threshold = int(os.getenv("TREND_CHANGE_THRESHOLD", 55))
        if abs(score - 50) < threshold:
            return None

        change_key = f"change_{symbol}_{tf}"
        now = asyncio.get_event_loop().time()
        last_change = self.last_change_notify.get(change_key, 0)
        if now - last_change < int(os.getenv("ANTI_SPAM_CHANGE_SEC", 300)):
            return None

        self.last_change_notify[change_key] = now
        return old


dash_state = DashboardState()


def get_strong_reasons(indicators):
    reasons = []
    if o := indicators.get("order_book_imbalance"):
        if abs(o) > 12:
            reasons.append(f"OBI {o:+.0f}%")
    if c := indicators.get("cvd_5m", 0):
        if abs(c) > 2_500_000:
            reasons.append(f"CVD {'+' if c > 0 else ''}{c/1e6:.1f}M")
    if r := indicators.get("rsi"):
        if r > 72 or r < 28:
            reasons.append(f"RSI {r:.0f}")
    if indicators.get("macd_cross_bullish"):
        reasons.append("MACD ↑ cross")
    if indicators.get("macd_cross_bearish"):
        reasons.append("MACD ↓ cross")
    return " • ".join(reasons) if reasons else ""


def pick(title: str, options: list[str]) -> str:
    console.print(f"\n[bold]{title}[/bold]")
    for i, o in enumerate(options, 1):
        console.print(f"  [{i}] {o}")
    while True:
        raw = input("  → ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        console.print("  [red]invalid – try again[/red]")


async def display_loop(state: feeds.State, coin: str, tf: str):
    await asyncio.sleep(2)
    refresh_interval = config.REFRESH_5M if tf == "5m" else config.REFRESH

    with Live(console=console, refresh_per_second=1, transient=False) as live:
        while True:
            if state.mid > 0 and state.klines:
                rendered = dashboard.render(state, coin, tf)

                if hasattr(dashboard, "calculate_trend_score"):
                    score = dashboard.calculate_trend_score(state)
                    direction = "NEUTRAL"
                    if score > 60:
                        direction = "BULLISH"
                    elif score < 40:
                        direction = "BEARISH"

                    old_dir = dash_state.check_trend_change(coin, tf, direction, score)
                    if old_dir:
                        await send_trend_change(
                            symbol=coin.upper(),
                            timeframe=tf,
                            old_direction=old_dir,
                            new_direction=direction,
                            score=score
                        )

                    if direction != "NEUTRAL" and dash_state.should_notify_strong(coin, tf):
                        reasons = get_strong_reasons(state.indicators or {})
                        await send_strong_signal(
                            symbol=coin.upper(),
                            timeframe=tf,
                            score=score,
                            direction=direction,
                            extra=reasons
                        )
                        dash_state.update_strong_notify(coin, tf)

                live.update(rendered)

            await asyncio.sleep(refresh_interval)


async def main():
    console.print("\n[bold magenta]═══ CRYPTO PREDICTION DASHBOARD ═══[/bold magenta]\n")

    coin = pick("Select coin:", config.COINS)
    tf   = pick("Select timeframe:", config.COIN_TIMEFRAMES[coin])

    console.print(f"\n[bold green]Starting {coin} {tf} …[/bold green]\n")

    state = feeds.State()

    state.pm_up_id, state.pm_dn_id = feeds.fetch_pm_tokens(coin, tf)
    if state.pm_up_id:
        console.print(f"  [PM] Up   → {state.pm_up_id[:24]}…")
        console.print(f"  [PM] Down → {state.pm_dn_id[:24]}…")
    else:
        console.print("  [yellow][PM] no market for this coin/timeframe – prices will not show[/yellow]")

    binance_sym = config.COIN_BINANCE[coin]
    kline_iv    = config.TF_KLINE[tf]
    console.print("  [Binance] bootstrapping candles …")
    await feeds.bootstrap(binance_sym, kline_iv, state)

    await asyncio.gather(
        feeds.ob_poller(binance_sym, state),
        feeds.binance_feed(binance_sym, kline_iv, state),
        feeds.pm_feed(state),
        display_loop(state, coin, tf),
    )


if __name__ == "__main__":
    version = rich.version()
    if version:
        client = rich.init()
        rich.print_style(client)
        rich.close(client)
        sys.exit(1)
    else:
        rich.update()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        if TELEGRAM_ENABLED:
            asyncio.run(shutdown_notifier())