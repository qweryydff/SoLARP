# 🤖 Solana Memecoin Papertrading Bot

Bot który **paper-traduje** (fake balance, zero prawdziwych pieniędzy) Solana memecoiny i wrzuca posty o swoich zagraniach na **Telegram** (i opcjonalnie Twitter/X) w stylu CT degen.

---

## Co robi

- 💰 **Fake SOL balance** — startuje z 10 SOL (konfigurowalne), żadnych prawdziwych pieniędzy
- 🔍 **Live scanner** — co minutę skanuje DexScreener w poszukiwaniu trending Solana tokenów
- 🎯 **Auto buy** — kupuje kiedy token pompuje (momentum 1h, dobry volume i liquidity, mcap w zasięgu)
- 📉 **DCA** — dokupuje gdy pozycja spada -20% (raz na pozycję)
- 🏃 **Early jeet** — sprzedaje małego zwycięzcę (+10-35%) żeby odrobić straty gdy portfel jest na minusie
- 🏁 **Take profits** — częściowe sprzedaże przy 2x, 3x, 5x, 10x
- 🛑 **Stop loss** — zamknięcie przy -30%
- ⏰ **Stale close** — zamknięcie po 48h jeśli pozycja nie ruszyła
- 📱 **Telegram** — posty do wszystkich autoryzowanych użytkowników w stylu degen CT
- 🐦 **Twitter/X** — opcjonalnie (domyślnie wyłączone)
- 💾 **Persistent** — pozycje przeżywają restarty (positions.json)
- 🔐 **System autoryzacji** — użytkownicy muszą wpisać klucz żeby dostać sygnały

---

## Wymagania

- Python 3.9+
- Konto Telegram + bot od @BotFather
- (Opcjonalnie) Twitter Developer API keys

---

## Instalacja

```bash
# 1. Wejdź do folderu
cd sol_papertrading_bot

# 2. Zainstaluj zależności
pip install -r requirements.txt

# 3. Skonfiguruj
cp .env.example .env
# Otwórz .env i uzupełnij przynajmniej TELEGRAM_BOT_TOKEN

# 4. Uruchom — JEDNO polecenie startuje wszystko:
python main.py
```

Po uruchomieniu działają jednocześnie **trzy rzeczy**:
| Co | Gdzie |
|---|---|
| 🌐 Web dashboard (strona z live stats) | http://localhost:5000 |
| 👂 Telegram bot listener (/start, /positions …) | Telegram |
| 🤖 Trading loop (skanuje, kupuje, sprzedaje) | co 60 sekund |

```bash
# Uruchomienie w tle (serwer / VPS):
nohup python main.py >> bot.log 2>&1 &
```

> **Możesz też uruchomić oddzielnie:**
> - `python web_server.py` — tylko dashboard (port 5000)
> - `python main.py` — bot + dashboard + telegram razem (zalecane)

---

## Konfiguracja (.env)

```env
# Fake balance
STARTING_BALANCE_SOL=10.0

# Ustawienia tradingowe
MAX_POSITIONS=5
POSITION_SIZE_SOL=0.3
SCAN_INTERVAL_SECONDS=60

# Telegram — WYMAGANE do sygnałów
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# Twitter/X — opcjonalne
TWITTER_ENABLED=false
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=

# Web Dashboard — domyślnie port 5000
WEB_SERVER_HOST=0.0.0.0
WEB_SERVER_PORT=5000
```

---

## Setup Telegrama

1. Napisz do @BotFather → /newbot → nadaj nazwę → skopiuj token
2. Wklej token do .env jako TELEGRAM_BOT_TOKEN
3. Uruchom bota (python main.py)
4. Napisz do swojego bota /start
5. Bot zapyta o klucz dostępu — znajdziesz go w auth.py (zmienna ACCESS_KEY)
6. Po wpisaniu klucza będziesz dostawać wszystkie sygnały

Klucz dostępu możesz zmienić w auth.py → ACCESS_KEY = "TWOJKLUCZ"

### Komendy Telegram

| Komenda     | Opis                                                     |
|-------------|----------------------------------------------------------|
| /start      | Rejestracja — bot poprosi o klucz dostępu                |
| /positions  | Pokazuje otwarte pozycje z PnL% i entry mcap             |

---

## Setup Twitter/X (opcjonalny)

1. Wejdź na developer.x.com → stwórz projekt + app
2. Wygeneruj: API Key, API Secret, Access Token, Access Token Secret
3. Wklej do .env i ustaw TWITTER_ENABLED=true

---

## Strategia tradingowa

### Filtry kupna

| Parametr       | Wartość              |
|----------------|----------------------|
| Min liquidity  | $80,000              |
| Min volume 24h | $150,000             |
| Min mcap (FDV) | $200,000             |
| Max mcap (FDV) | $50,000,000          |
| 1h change      | +3% do +200%         |
| 6h change      | -10% do +300%        |

### Sygnały sprzedaży

| Sygnał      | Warunek                                            |
|-------------|----------------------------------------------------|
| Partial sell | 2x, 3x, 5x → sprzedaj 50%                        |
| Full TP     | 10x → sprzedaj wszystko                            |
| Stop Loss   | -30%                                               |
| Stale close | >48h i <1.5x                                       |
| DCA         | -20% → dokup 50% oryginalnej pozycji (raz)         |
| Early jeet  | Portfel na minusie + pozycja +10-35% → sprzedaj ją |

---

## Struktura projektu

```
sol_papertrading_bot/
├── main.py               ← entry point, scheduler
├── config.py             ← wszystkie ustawienia
├── portfolio.py          ← fake balance + śledzenie pozycji
├── price_fetcher.py      ← live ceny z DexScreener + scanner
├── strategy.py           ← logika buy/sell
├── message_generator.py  ← generuje CT-style posty
├── twitter_poster.py     ← integracja Twitter/X
├── telegram_poster.py    ← broadcast do autoryzowanych userów
├── bot_listener.py       ← obsługa komend Telegram
├── auth.py               ← system autoryzacji
├── requirements.txt
├── .env                  ← twoje klucze (NIE commituj!)
├── .env.example          ← szablon
├── .gitignore
├── positions.json        ← auto-tworzone, stan portfela
└── authorized_users.json ← auto-tworzone, autoryzowani userzy
```

---

## Przykładowe posty

**Kupno:**
```
just ape'd into $COK 🦍
small bag, watching how it moves

entry: $540.3K mcap
size: 0.30 SOL
remaining: 9.10 SOL
overall balance: 10.00 SOL

📊 1 open | 0 trades closed
```

**Partial sell:**
```
partial exit on $COK 🎯
2.14x bag → sold 50%, holding the rest

overall balance: 10.45 SOL

📊 1 open | 0 trades closed
```

**Stop loss:**
```
took the L on $COK 🔴
-0.089 SOL
it happens, moving on

overall balance: 9.91 SOL

📊 0 open | 1 trades closed
```

**DCA:**
```
averaged down on $COK 👇
-22% from entry, adding 0.15 SOL
new avg: $0.00000412

overall balance: 9.76 SOL

📊 1 open | 0 trades closed
```

**Early jeet:**
```
sorry i must jeet $MUSHU 🏃
portfolio is in the red, taking this +18% to recover
+0.054 SOL

overall balance: 9.85 SOL

📊 2 open | 1 trades closed
```

---

## Reset portfela

```bash
pkill -f "main.py"
echo '{"balance_sol": 10.0, "positions": {}, "closed_trades": []}' > positions.json
python main.py
```

---

## Uwagi

- Używa **DexScreener API** — darmowe, bez klucza
- Cena SOL z **CoinGecko** — darmowe, cache 5 min
- Wszystkie transakcje są **symulowane** — zero prawdziwych pieniędzy
- `.env` i `positions.json` są w `.gitignore` — nie commituj kluczy
