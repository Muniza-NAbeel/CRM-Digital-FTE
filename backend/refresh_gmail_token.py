from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import os

# Gmail ke liye correct scopes (sirf email bhejne ke liye)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def main():
    print("🔄 Gmail Token Refresh Script Starting...\n")

    if not os.path.exists('credentials.json'):
        print("❌ Error: credentials.json file nahi mila!")
        print("Google Cloud Console se credentials.json download karke yahan rakho.")
        return

    # Delete old token.json to force new refresh token
    if os.path.exists('token.json'):
        print("🗑️  Deleting old token.json to force new refresh token...")
        os.remove('token.json')

    print("Browser khulega → Apna Gmail account login karo → Allow kar do")
    print("⚠️  IMPORTANT: Make sure to grant ALL permissions!")

    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',
        SCOPES
    )

    # Yeh automatically browser kholega aur localhost use karega
    # access_type=offline ensures we get a refresh token
    creds = flow.run_local_server(
        port=0,
        open_browser=True,
        prompt='consent',  # Force consent screen to get refresh token
        access_type='offline'  # Request refresh token
    )

    # Token save kar do
    with open('token.json', 'wb') as token:
        pickle.dump(creds, token)

    # Verify refresh token exists
    if creds.refresh_token:
        print("\n✅ Success! Naya token.json file ban gaya hai.")
        print(f"   Refresh token: {creds.refresh_token[:20]}...")
        print("Ab apna normal server (run_both.py) restart kar do.")
    else:
        print("\n❌ ERROR: Refresh token nahi mila!")
        print("   Dobara try karo aur ensure karo ke sab permissions grant karo.")

if __name__ == '__main__':
    main()