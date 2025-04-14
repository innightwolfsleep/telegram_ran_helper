# Telegram RAN Helper Bot

This is a Telegram bot that assists radio engineers in various... 
- calculating frequencies from channel numbers,
- converting dBm to watts and vice versa,
- calculating eNodeB from ECI, 
- describing IP networks.

## Installation
```
git clone https://github.com/innightwolfsleep/telegram-ran-helper.git
cd telegram-ran-helper
pip install python-telegram-bot ipcalc
```

### Running

1. **Obtain a token for your Telegram bot**: Create a new bot in [BotFather](https://t.me/BotFather) and get the token.
2. **Run the bot**:
```
python telegram_ran_helper.py <your_tg_token>
```
