# gmail-accessor
# 📧 Gmail Attachment Processor and Text Extractor

This Apify Actor connects to a user's Gmail account using the Google API, searches for emails based on a flexible query, and extracts text content from specific attachments (e.g., **PDFs**).

It is purpose-built for automation workflows, such as extracting structured data from documents like **Rate Confirmations**, **Invoices**, or **Purchase Orders** to feed into an LLM or another system.

-----

## ✨ Key Features

  * **Secure OAuth 2.0:** Uses a long-lived **Refresh Token** (`GMAIL_CREDENTIALS_JSON`) to access the Gmail API without storing passwords.
  * **Flexible Filtering:** Leverages the full power of Gmail search operators (e.g., `subject:`, `from:`, `after:`) via the `gmailQuery` input.
  * **Targeted Extraction:** Processes only attachments matching the specified `attachmentMimeTypes`.
  * **PDF to Text Conversion:** Utilizes the `pdfminer.six` library to robustly convert PDF attachments into clean, searchable plain text.
  * **LLM-Ready Output:** Stores the extracted text in a structured dataset, ready for AI and data analysis.

-----

## ⚙️ Input Configuration

The Actor requires the following JSON input fields. Note the exact casing for the mandatory credential field.

| Field Name | Type | Required | Description | Default Value |
| :--- | :--- | :--- | :--- | :--- |
| **`GMAIL_CREDENTIALS_JSON`** | `String` | **Yes** | The full, unedited JSON string containing the Gmail OAuth 2.0 refresh token. **Critical for authentication.** | - |
| `gmailQuery` | `String` | No | A standard Gmail search query to filter messages. Example: `subject:"invoice" after:2024/01/01`. | `'subject:"Rate Confirmation for order #" has:attachment from:@scotlynn.com'` |
| `attachmentMimeTypes` | `Array<String>` | No | A list of MIME types for attachments to target. The Actor processes the **first matching attachment** found in an email. | `['application/pdf']` |

### Example Input JSON

```json
{
  "GMAIL_CREDENTIALS_JSON": "YOUR_FULL_OAUTH_JSON_STRING_HERE",
  "gmailQuery": "subject:invoice after:2024/02/01 before:2024/03/01 has:attachment",
  "attachmentMimeTypes": ["application/pdf"]
}
```

-----

## 🔒 Authentication Setup (How to get `GMAIL_CREDENTIALS_JSON`)

The `GMAIL_CREDENTIALS_JSON` is an OAuth 2.0 token object required for the Actor to access your Gmail. You must generate this object once outside of Apify.

### 1\. Google Cloud Console Setup

1.  Navigate to the **Google Cloud Console** and create or select a project.
2.  Enable the **Gmail API** service for your project.
3.  Go to **APIs & Services \> Credentials** and click **Create Credentials \> OAuth client ID**.
4.  Select **Application type: Desktop app** (this is the simplest type for generating the refresh token locally).
5.  Save your generated **Client ID** and **Client Secret**.

### 2\. Token Generation Script

A local Python script must be run to generate the final token string. This process guides you through authorizing your application with Google and ensures a long-lived **refresh token** is issued.

The resulting script output is a single, complete JSON string containing the `client_id`, `client_secret`, and the required `refresh_token`.

**This entire output JSON string is the value you must provide for the `GMAIL_CREDENTIALS_JSON` input field.**

-----

## 📊 Output Dataset Structure

The Actor pushes one record to the default dataset for every email attachment successfully processed and converted to text.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `messageId` | `String` | The unique ID of the Gmail message. |
| `subject` | `String` | The subject line of the email. |
| `date` | `String` | The date the email was received. |
| `attachmentName` | `String` | The file name of the extracted attachment. |
| `gmailQueryUsed` | `String` | The search query used for this run. |
| `targetMimes` | `Array<String>` | The MIME types the Actor was configured to search for. |
| **`attachmentContentText`** | **`String`** | **The full, extracted plain text content of the attachment (ready for downstream processing).** |

### Example Dataset Item

```json
{
  "messageId": "19028a314b1f...",
  "subject": "Rate Confirmation for order #1296137",
  "date": "Fri, 5 Dec 2025 10:00:00 -0500",
  "attachmentName": "order_confirmation_1296137.pdf",
  "gmailQueryUsed": "subject:\"Rate Confirmation for order #\"...",
  "targetMimes": ["application/pdf"],
  "attachmentContentText": "Rate Confirmation\n\n1296137\n\nSCOTLYNN\n\nScotlynn USA Division V24.2\n 9597 Gulf Research Lane..."
}
```
