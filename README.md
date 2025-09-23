# Sycon Cloud API — Production Docs
<a href="https://www.sycon.fr">
  <img src="docs/assets/logo.webp" alt="Sycon" align="right" width="240">
</a>

[![Sycon](https://img.shields.io/badge/Sycon-1.2.0-0bf57a.svg)](#)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-blue.svg)](#)
[![Docs](https://img.shields.io/badge/SwaggerUI-success.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](#)

Ce dépôt contient la documentation publique de l’API Sycon Cloud.

- **Swagger :** <https://hello-sycon.github.io/sycon-api-production/>

## Démarrage rapide

1. **Login** → `POST /auth/login` (récupérez les en-têtes `Authorization` & `Renew`)
2. **Lister vos devices** → `GET /api/devices`
3. **Récupérer des données** → `GET /api/devices/{deviceId}/{field}/data/raw?start=...&end=...&tailLimit=...`

Exemples : `examples/`

## Guide détaillé

la documentation complète [docs/guide.md](docs/guide.md)

## Spécification Sycon en OpenAPI
Spécification 1.2.0 : `docs/v1.2.0/sycon-cloud-api`.

## Support
- Site : <https://www.sycon.fr/>
- Contact : <hello@sycon.fr>
