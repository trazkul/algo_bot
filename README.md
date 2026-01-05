# Algo Bot

Короткое описание: бот на Python для фьючерсной торговли. Делает цикл
BUY → пауза → SELL, чтобы нарастить торговый объём. Поддерживает Bybit
и Binance (testnet/mainnet через `config.yaml`).

## Быстрый старт

1) Установить зависимости:
```bash
pip install -r requirements.txt
```

2) Заполнить `.env` (ключи не коммитить):
```env
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

3) Настроить `config.yaml` и запустить:
```bash
python -m bot.main
```

## Основные настройки (`config.yaml`)

Пример:
```yaml
bot:
  exchange: BYBIT        # биржа: bybit или binance
  symbol: BTCUSDT        # торговая пара
  category: linear       # категория рынка (Bybit)
  account_type: UNIFIED  # тип аккаунта (Bybit)
  order_qty: "0.001"     # объем ордера в базовой монете
  interval_sec: 5        # пауза между циклами, сек
  recv_window: 5000      # окно валидности запроса, мс
  fill_delay_ms: 300     # пауза между BUY и SELL, мс
  max_volume_usdt: "1000" # лимит объема, USDT
  dry_run: false         # false — реальные ордера, true — только лог
  testnet: true          # testnet=true, mainnet=false
```

## Команды

Запуск бота:
```bash
python -m bot.main
```

Сервисные команды:
```bash
python -m bot.tools balances       # вывести балансы (Bybit)
python -m bot.tools open-orders    # список открытых ордеров по bot.symbol
python -m bot.tools cancel-all     # отменить ордера по bot.symbol
python -m bot.tools close-position # закрыть позицию по bot.symbol
python -m bot.tools close-all      # отменить ордера и закрыть позицию по bot.symbol
```

## Примечания

- По Binance минимальный notional может быть ≥ 100 USDT.
- Логи пишутся в терминал и в файл `bot.log`.
- Use small quantities for testing.
- This is a minimal framework; extend risk controls before mainnet.
