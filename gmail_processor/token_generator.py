# token_generator.py
import os
from google_auth_oauthlib.flow import InstalledAppFlow
import json

# The SCOPE from your Apify Actor
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly'] 

def generate_credentials_json():
    """Performs the OAuth flow and prints the resulting JSON credentials."""
    
    # 1. Start the flow

    
    # This automatically looks for client_secret.json
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json', 
        scopes=SCOPES
    )
    
    # Use run_local_server for the Desktop App flow
    credentials = flow.run_local_server(
        port=0, # Choose a random available port
        access_type='offline', # MANDATORY: Ensures a refresh_token is returned
        prompt='consent' # MANDATORY: Forces the consent screen, ensuring a refresh_token
    )
    
    # 2. Get the required JSON string
    creds_json = credentials.to_json()
    
    # 3. Print the result
    print("\n\n#####################################################")
    print("COPY THIS ENTIRE JSON STRING (GMAIL_CREDENTIALS_JSON):")
    print("#####################################################\n")
    # This JSON string contains the refresh_token that Apify needs
    print(creds_json)

if __name__ == '__main__':
    # Setting this allows the use of HTTP for the local redirect
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' 
    generate_credentials_json()