# Exploitation

## Architecture

```text
nginx :443
├── /            → GeneWeb 127.0.0.1:2317
└── /genealogy/  → Genealogy Web 127.0.0.1:8000
```

Genealogy Web est lancé par systemd. Uvicorn écoute uniquement sur
`127.0.0.1:8000`.

## Configuration locale

Les variables locales sont définies dans `~/.genealogy-web.env` :

```ini
GEOAPIFY_API_KEY=...
GENEWEB_PORTRAITS_DIR=/home/ubuntu/geneweb/distribution/bases/images/Famille
GENEALOGY_GEDCOM_DIR=/home/ubuntu/exports/gedcom
APP_ROOT_PATH=/genealogy
```

Ce fichier peut contenir des secrets et des données propres à la machine. Il
ne doit jamais être versionné.

Le `.bashrc` se place dans `~/genealogy-web`, active `.venv`, puis charge
`~/.genealogy-web.env` avec `set -a`.

## Service

Commandes utiles :

```bash
systemctl status genealogy-web
sudo systemctl restart genealogy-web
journalctl -u genealogy-web -f
```

Le service charge automatiquement le fichier `.ged` le plus récent de
`GENEALOGY_GEDCOM_DIR`.

## URLs

Lorsque le réseau l'autorise :

```text
https://genedaweb.duckdns.org/
https://genedaweb.duckdns.org/genealogy/
```

`/genealogy/` est protégé par l'authentification Basic de nginx.

## Accès depuis le PC professionnel

Le fichier `hosts` contient :

```text
127.0.0.1 genedaweb.duckdns.org
```

Configuration SSH utilisateur :

```sshconfig
Host geneweb
    HostName <SERVER_IP>
    User ubuntu
    IdentityFile <SSH_KEY_PATH>
    ServerAliveInterval 30
    ServerAliveCountMax 6
    LocalForward 8443 127.0.0.1:443
```

La documentation versionnée ne doit contenir ni adresse IP publique réelle ni
chemin réel de clé privée.

Connexion interactive :

```bash
ssh geneweb
```

Tunnel seul :

```bash
ssh -N geneweb
```

Puis ouvrir :

```text
https://genedaweb.duckdns.org:8443/
https://genedaweb.duckdns.org:8443/genealogy/
```

L'ancien tunnel `8000 → 8000` n'est plus nécessaire.

## Nginx

Principe de proxy :

```text
/genealogy/ → http://127.0.0.1:8000/
```

Après une modification de configuration :

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Ne pas versionner de certificat, hash de mot de passe ou autre secret nginx.

## Diagnostic rapide

```bash
curl http://127.0.0.1:8000/health
systemctl status genealogy-web
journalctl -u genealogy-web -n 100 --no-pager
sudo nginx -t
```

`/health` doit notamment indiquer `source=AUTO`, le fichier GEDCOM chargé et
`load_error=null`.
