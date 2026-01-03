# Tavern Taps

A lightweight, fantasy-themed Untappd-style clone for your D&D tavern. Add, edit, and manage beers from the admin panel and share the tap list with your party.

## Features

- Public tap list with beer detail pages
- Admin panel to add, edit, and delete brews
- SQLite storage (no external database required)
- Simple theme ready for tavern flavor

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=changeme
export SECRET_KEY=dev-secret
python app.py
```

Visit `http://localhost:5000` for the tap list and `http://localhost:5000/admin` to manage beers.

## Deploy on Hetzner (Docker + Caddy)

The quickest path on a Hetzner VPS is running the app with Docker and using Caddy for HTTPS.

### 1) Create a server

- Provision a Ubuntu 22.04 VPS in Hetzner Cloud.
- Point your domain (e.g. `tavern.yourdomain.com`) to the server’s public IP.

### 2) Install Docker

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
```

### 3) Copy the project to the server

From your local machine:

```bash
rsync -av --exclude '.git' ./ user@your-server-ip:/opt/tavern-taps
```

### 4) Create environment variables

```bash
cd /opt/tavern-taps
cat <<'ENV' > .env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=super-secret
SECRET_KEY=replace-me-with-a-long-random-string
ENV
```

### 5) Run the container

```bash
docker build -t tavern-taps .
docker run -d \
  --name tavern-taps \
  --env-file .env \
  -p 5000:5000 \
  -v /opt/tavern-taps/data:/opt/tavern-taps/data \
  tavern-taps
```

### 6) Add HTTPS with Caddy

```bash
sudo apt-get install -y caddy
```

Create `/etc/caddy/Caddyfile`:

```
tavern.yourdomain.com {
  reverse_proxy 127.0.0.1:5000
}
```

Reload Caddy:

```bash
sudo systemctl reload caddy
```

Your site should now be live at `https://tavern.yourdomain.com`.

## Admin credentials

Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`. Change `SECRET_KEY` in production.

## Data storage

The SQLite database is stored at `data/tavern.db` inside the container. The Docker run command above maps it to `/opt/tavern-taps/data` on the host so it persists across restarts.
