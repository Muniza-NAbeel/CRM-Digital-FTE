from dotenv import dotenv_values
from pathlib import Path

env_path = Path('.env').absolute()
print(f'Loading from: {env_path}')

values = dotenv_values(env_path)
print('Keys found:', list(values.keys()))
print()
print('APP_TWILIO_ACCOUNT_SID:', values.get('APP_TWILIO_ACCOUNT_SID'))
print('APP_TWILIO_AUTH_TOKEN:', values.get('APP_TWILIO_AUTH_TOKEN'))
print('APP_GMAIL_CLIENT_ID:', values.get('APP_GMAIL_CLIENT_ID'))
