
**Local quickstart**:

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Set password for local testing (option A: environment variable):

```bash
set STREAMLIT_PASSWORD=yourpassword
```

3. Run Streamlit:

```bash
streamlit run app.py
```

Notes

- This scaffold uses an in-memory datastore for local testing (`datastore_client.py`). To use GCP Datastore replace that implementation with `google.cloud.datastore.Client()` calls and provide credentials via `GOOGLE_APPLICATION_CREDENTIALS` or Streamlit secrets.

Deployment (Streamlit Cloud)

1. Push your repository to GitHub (public if using free Streamlit sharing).
2. On share.streamlit.io, connect the GitHub repo and branch.
3. Add secrets (Settings -> Secrets) with keys used by the app:

Example `secrets.toml` values:

```toml
# plain password (not recommended for production)
password = "yourpassword"

# or hashed password (preferred): generate with scripts/generate_password_hash.py
password_hash = "<PASTE_HASH_HERE>"

# GCP service account JSON (if using Datastore in production)
# set as a multiline secret named 'gcp_service_account'
gcp_service_account = "{...}"
```

If using a service account JSON, set `GOOGLE_APPLICATION_CREDENTIALS` environment variable on the host to point to a file path containing the JSON, or modify `app` startup to load the JSON from `st.secrets["gcp_service_account"]` and write it to a temporary file before initializing the Datastore client.

Local emulator

- To test Datastore locally, install `gcloud` and run the emulator. Set `GOOGLE_APPLICATION_CREDENTIALS` or `USE_GCP_DATASTORE=1` as needed.

Security notes

- Prefer `password_hash` instead of `password` in production. Use `scripts/generate_password_hash.py` to create a hash.
- Keep service account JSON secret — store it in Streamlit secrets, not in the repo.
