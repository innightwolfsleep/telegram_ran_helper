# Telegram RAN Helper Bot

This is a Telegram bot that assists radio engineers in various... 
- calculating frequencies from channel numbers,
- converting dBm to watts and vice versa,
- calculating eNodeB from ECI, 
- describing IP networks.
- daemon and simple script mode

## Installation
```
git clone https://github.com/innightwolfsleep/telegram_ran_helper
cd telegram_ran_helper
pip install -r requirements.txt
```

### Running

1. **Obtain a token for your Telegram bot**: Create a new bot in [BotFather](https://t.me/BotFather) and get the token.
2. **Run the bot (as daemon)**:
```
python telegram_ran_helper.py <your_tg_token> y
```
