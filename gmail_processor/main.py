import os
import io
import json
import base64
from typing import Dict, Any, Optional, List
import asyncio

# Apify SDK imports
from apify import Actor
from apify_client import ApifyClient

# Google API imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# PDF processing imports
from pdfminer.high_level import extract_text_to_fp
from io import StringIO, BytesIO

# --- CONFIGURATION ---

# Default configuration values
DEFAULT_GMAIL_QUERY = 'subject:"Rate Confirmation for order #" has:attachment from:@scotlynn.com'
DEFAULT_MIME_TYPES = ['application/pdf']
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# --- HELPER FUNCTIONS ---

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extracts plain text content from PDF file bytes using pdfminer.six."""
    output_string = StringIO()
    # Wrap bytes in a file-like object for pdfminer
    with BytesIO(pdf_bytes) as fin:
        # Use a high-level function for simple text extraction
        extract_text_to_fp(fin, output_string)
    return output_string.getvalue().strip()


def get_attachment_data(service: Any, user_id: str, msg_id: str, att_id: str) -> Optional[bytes]:
    """Fetches and decodes a specific attachment's binary data."""
    try:
        att = service.users().messages().attachments().get(
            userId=user_id, messageId=msg_id, id=att_id
        ).execute()

        # The data is base64url encoded
        data = att.get('data')
        if data:
            return base64.urlsafe_b64decode(data.encode('UTF-8'))
    except HttpError as error:
        Actor.log.error(f"Failed to fetch attachment {att_id}: {error}")
    return None

def find_mime_parts(parts: List[Dict[str, Any]], target_mimes: List[str]) -> List[Dict[str, Any]]:
    """Recursively search through message parts for target MIME types."""
    found_parts = []
    
    if not parts:
        return found_parts

    for part in parts:
        # Check current part
        if part.get('mimeType') in target_mimes and part.get('body', {}).get('attachmentId'):
            # Only include parts that have an attachment ID
            found_parts.append(part)
        
        # Check nested parts (e.g., in multipart messages)
        if 'parts' in part:
            found_parts.extend(find_mime_parts(part['parts'], target_mimes))
            
    return found_parts

# --- MAIN ACTOR LOGIC ---

async def main():
    """The main function of the Apify Actor."""
    async with Actor:
        Actor.log.info('Actor started.')

        # 1. Get Input and Configuration
        actor_input = await Actor.get_input() or {}
        
        # MANDATORY: The Gmail OAuth 2.0 credentials
        creds_json_str = actor_input.get('gmail_credentials.json') 
        if not creds_json_str:
            Actor.log.error("GMAIL_CREDENTIALS_JSON not provided in Actor input.")
            return
            
        # OPTIONAL: The user-defined search query
        gmail_query = actor_input.get('gmailQuery', DEFAULT_GMAIL_QUERY)
        # OPTIONAL: The list of target MIME types
        target_mimes = actor_input.get('attachmentMimeTypes', DEFAULT_MIME_TYPES)

        Actor.log.info(f"Using Search Query: '{gmail_query}'")
        Actor.log.info(f"Targeting MIME Types: {', '.join(target_mimes)}")

        # Load Credentials
        try:
            creds_data = json.loads(creds_json_str)
            creds = Credentials.from_authorized_user_info(info=creds_data, scopes=SCOPES)
        except Exception as e:
            Actor.log.error(f"Error loading credentials: {e}")
            return

        # 2. Initialize Gmail Service
        try:
            service = build('gmail', 'v1', credentials=creds)
            user_id = 'me'
            Actor.log.info("Successfully initialized Gmail API service.")
        except Exception as e:
            Actor.log.error(f"Failed to build Gmail service: {e}")
            return

        # 3. Search for Emails
        try:
            response = service.users().messages().list(
                userId=user_id,
                q=gmail_query
            ).execute()
        except HttpError as error:
            Actor.log.error(f"Gmail search failed: {error}")
            return

        messages = response.get('messages', [])
        Actor.log.info(f"Found {len(messages)} matching email(s).")
        
        if not messages:
            Actor.log.info("No matching emails found. Exiting.")
            return
        
        # 4. Process Each Message
        
        for msg_count, message in enumerate(messages, 1):
            msg_id = message['id']
            Actor.log.info(f"[{msg_count}/{len(messages)}] Processing message ID: {msg_id}")

            try:
                # Get the full message content
                msg = service.users().messages().get(
                    userId=user_id, id=msg_id, format='full'
                ).execute()
                
                # Extract basic metadata
                headers = {h['name']: h['value'] for h in msg['payload']['headers']}
                subject = headers.get('Subject', 'No Subject')
                date = headers.get('Date', 'No Date')
                
                # Recursively search for attachments
                all_parts = [msg['payload']] if 'parts' not in msg['payload'] else msg['payload']['parts']
                target_attachments = find_mime_parts(all_parts, target_mimes)

                attachment_content_text = None
                attachment_filename = None
                
                if target_attachments:
                    # We process only the first found target attachment
                    part = target_attachments[0]
                    filename = part.get('filename', 'untitled_attachment')
                    att_id = part['body']['attachmentId']
                    
                    Actor.log.info(f"  -> Found target attachment: {filename} (MIME: {part.get('mimeType')})")
                    
                    attachment_bytes = get_attachment_data(service, user_id, msg_id, att_id)
                    
                    if attachment_bytes and part.get('mimeType') == 'application/pdf':
                        # Handle PDF to Text
                        try:
                            attachment_content_text = extract_pdf_text(attachment_bytes)
                            attachment_filename = filename
                            Actor.log.info(f"  -> Successfully extracted text from PDF. Size: {len(attachment_content_text)} chars.")
                        except Exception as e:
                            Actor.log.warning(f"  -> Failed to extract text from PDF: {e}")
                            
                    elif attachment_bytes:
                        # Handle other binary types (if added to target_mimes)
                        # For simple LLM processing, we might base64 encode it or process it 
                        # using another library (e.g., python-docx for .docx files)
                        # For this example, we'll store the text of the message body if 
                        # we couldn't process the attachment.
                        attachment_filename = filename
                        attachment_content_text = f"Binary content of {filename} was not processed to text. Size: {len(attachment_bytes)} bytes."
                        Actor.log.warning(f"  -> Attachment type {part.get('mimeType')} not automatically converted to text.")


                # 5. Store Result in Apify Dataset
                if attachment_content_text:
                    record = {
                        "messageId": msg_id,
                        "subject": subject,
                        "date": date,
                        "attachmentName": attachment_filename,
                        "gmailQueryUsed": gmail_query,
                        "targetMimes": target_mimes,
                        # The full, extracted text content ready for the LLM
                        "attachmentContentText": attachment_content_text,
                        # This LLM-ready field contains the text for downstream processing
                    }
                    await Actor.push_data(record)
                    Actor.log.info(f"  -> Pushed data for message: {msg_id}")
                else:
                    Actor.log.warning(f"  -> No usable target attachment found or extraction failed for message {msg_id}. Skipping.")

            except Exception as e:
                Actor.log.error(f"An unexpected error occurred processing message {msg_id}: {e}")

        Actor.log.info('Actor finished.')

if __name__ == '__main__':
    asyncio.run(main())