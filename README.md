# Arjay May Hardware — Python Sales Analytics Dashboard

A standalone Python analytics dashboard built with **Streamlit**, showing
live sales, revenue, top products, and inventory health for Arjay May
Hardware.

## How it works

The main store system (login, POS, orders, products) is PHP + MySQL,
hosted on InfinityFree. InfinityFree blocks external apps from connecting
to its databases directly, so this dashboard doesn't try to — instead it
calls a small, secured PHP file (`admin/api/analytics.php`) already
running on that same server. That file reads the real database and hands
back the numbers as JSON. This app just displays them.

No sales data is stored here — every page load pulls fresh numbers live
from the store's database through that API.

## Local setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml with the real API_BASE_URL and API_KEY
streamlit run app.py
```

## Deploying for free (Streamlit Community Cloud)

1. Push this folder to a GitHub repo (public or private — either works).
2. Go to share.streamlit.io, sign in with GitHub, and deploy this repo,
   pointing at `app.py`.
3. In the app's **Settings → Secrets**, paste:
   ```
   API_BASE_URL = "https://your-domain.wuaze.com/admin/api/analytics.php"
   API_KEY = "the-real-key-from-config.php"
   ```
4. Deploy. The dashboard will be live at a free `*.streamlit.app` URL.

## Security note

`API_KEY` must match `ANALYTICS_API_KEY` in the PHP project's
`config/config.php`. Treat it like a password — never commit the real
value to GitHub (that's why it lives in Streamlit's Secrets manager, not
in this code).
