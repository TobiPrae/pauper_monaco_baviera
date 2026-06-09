
**Local quickstart**:

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Add secrets to .streamlit/secrets.toml:


```bash
[service_account_key]
"type"= "service_account"
"project_id"= "..."
"private_key_id"= "..."
"private_key"= "..."
"client_email"= "..."
"client_id"= "..."
"auth_uri"= "https://accounts.google.com/o/oauth2/auth"
"token_uri"= "https://oauth2.googleapis.com/token"
"auth_provider_x509_cert_url"= "https://www.googleapis.com/oauth2/v1/certs"
"client_x509_cert_url"= "..."
"universe_domain"= "googleapis.com"
```

3. Configure .env file:
```bash
Create .env file in base folder and variable accordingly
For Development and Test(enables local_datastore.json): 
USE_GCP_DATASTORE=false
For Production(enables proper GCP Connection):
USE_GCP_DATASTORE=true
```

4. Run Streamlit:

```bash
streamlit run app.py
```
