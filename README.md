# Sycon Cloud API — Production Docs
<a href="https://www.sycon.fr">
  <img src="docs/assets/logo.webp" alt="Sycon" align="right" width="240">
</a>

[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-blue.svg)](#)
[![Docs](https://img.shields.io/badge/Docs-MkDocs%20or%20SwaggerUI-success.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](#)

Ce dépôt contient la documentation publique **production** de l’API Sycon Cloud.

- **Base URL :** <https://cloud.sycon.io>
- **Swagger UI :** <https://hello-sycon.github.io/sycon-api-production/>
- **Guide d’utilisation :** [docs/guide.md](docs/guide.md)

## Démarrage rapide

1. **Login** → `POST /auth/login` (récupérez les en-têtes `Authorization` & `Renew`)
2. **Lister vos devices** → `GET /api/devices`
3. **Récupérer des données** → `GET /api/devices/{deviceId}/{field}/data/raw?start=...&end=...&tailLimit=...`

Exemples : `examples/`

## Spécification OpenAPI
Spécification 3.1 : `docs/v3/sycon-cloud-api`.

## Support
- Site : <https://www.sycon.fr/>
- Contact : <hello@sycon.fr>
