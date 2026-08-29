# TibiaClaims Board Watcher

Bot Discorda, który cyklicznie odpytuje endpoint TibiaClaims:

```
https://api.tibiaclaims.com/api/v1/claim-servers/karmeya/board
```

i wysyła powiadomienia w formie **embedów** na wskazany kanał, gdy na tablicy
rezerwacji spawnów pojawi się zmiana (nowa rezerwacja, anulowanie, zmiana
statusu spawnu, start/koniec claima).

## Architektura

```
tibia_claims_bot/
├── main.py                 # punkt wejścia
└── tibia_claims_bot/
    ├── api_client.py        # klient HTTP (aiohttp) do API TibiaClaims
    ├── bot.py                # bot Discord (discord.py) + pętla odpytywania
    ├── config.py             # konfiguracja z .env
    ├── diff_engine.py        # logika porównywania dwóch snapshotów
    ├── models.py              # modele danych (Board, Spawn, Reservation)
    ├── notifier.py            # budowanie embedów Discord
    └── storage.py             # trwałe zapisywanie ostatniego stanu (JSON)
```

Bot **nie trzyma stanu tylko w pamięci** — każdy pobrany snapshot jest
zapisywany atomowo do pliku JSON (`STATE_FILE`), dzięki czemu restart bota
nie powoduje zalewu fałszywych powiadomień ani utraty historii.

### Wykrywane typy zmian

| Typ zdarzenia            | Kiedy występuje                                         |
|---------------------------|----------------------------------------------------------|
| 🆕 Nowa rezerwacja        | Pojawia się nowy wpis w `reservations` danego spawnu     |
| ❌ Rezerwacja anulowana   | Wpis znika z `reservations`                              |
| ▶️ Claim rozpoczęty        | Pole `current` zmienia się z `null` na rezerwację         |
| ⏹️ Claim zakończony        | Pole `current` zmienia się z rezerwacji na `null`         |
| 🔄 Zmiana statusu spawnu  | Pole `status` się zmienia (np. `available` → `upcoming`) |
| ➕ / ➖ Spawn dodany/usunięty | Spawn pojawia się lub znika z odpowiedzi API           |

## Wymagania

- Python 3.11+
- Konto bota na [Discord Developer Portal](https://discord.com/developers/applications)
  z tokenem oraz uprawnieniami `Send Messages` i `Embed Links` na docelowym kanale

## Instalacja

```bash
git clone <repo>
cd tibia_claims_bot
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Uzupełnij `.env`:

```env
DISCORD_TOKEN=twoj-token-bota
DISCORD_CHANNEL_ID=123456789012345678
TIBIA_CLAIMS_API_URL=https://api.tibiaclaims.com/api/v1/claim-servers/karmeya/board
POLL_INTERVAL_SECONDS=60
STATE_FILE=data/last_snapshot.json
LOG_LEVEL=INFO
```

## Uruchomienie

```bash
python main.py
```

Pierwsze uruchomienie tylko zapisuje bazowy snapshot (bez powiadomień —
nie ma jeszcze punktu odniesienia). Od drugiego cyklu odpytywania bot
zacznie porównywać kolejne pobrania i wysyłać embedy z wykrytymi zmianami.

## Uruchomienie jako usługa (systemd)

```ini
[Unit]
Description=TibiaClaims Board Watcher
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/tibia_claims_bot
ExecStart=/opt/tibia_claims_bot/.venv/bin/python main.py
Restart=on-failure
RestartSec=10
EnvironmentFile=/opt/tibia_claims_bot/.env

[Install]
WantedBy=multi-user.target
```

## Uwagi projektowe

- **Odporność na błędy sieci/API**: pojedynczy nieudany fetch nie crashuje
  bota — jest logowany, a po 3/10/30 kolejnych nieudanych próbach bot
  wysyła jedno powiadomienie ostrzegawcze na Discord (bez spamu przy każdej
  próbie).
- **Limity Discorda**: pojedyncza wiadomość może zawierać maksymalnie 10
  embedów; przy dużej liczbie zmian bot dzieli je na kilka wiadomości
  (`max_events_per_message` w `config.py` kontroluje też liczbę pól w
  jednym embedzie, by nie przekroczyć limitu 25 pól).
- **Atomowy zapis stanu**: `storage.py` zapisuje snapshot do pliku
  tymczasowego i podmienia go atomowo (`os.replace`), żeby awaria w trakcie
  zapisu nie skorumpowała pliku stanu.
- **Rozszerzalność**: dodanie nowego typu zdarzenia sprowadza się do
  dopisania wariantu w `ChangeType`, logiki w `diff_engine.py` oraz etykiety
  w `notifier.py`.

## Testowanie bez własnego bota

Jeśli chcesz najpierw sprawdzić logikę diffowania bez podłączania Discorda,
możesz zaimportować `diff_engine.diff_boards` i `models.Board` bezpośrednio
i przepuścić przez nie dwa przykładowe payloady JSON w interpreterze.
