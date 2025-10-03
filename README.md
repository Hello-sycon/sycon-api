# Guide d’utilisation — Sycon Cloud API
<a href="https://www.sycon.fr">
  <img src="docs/assets/logo.webp" alt="Sycon" align="right" width="240">
</a>

[![Sycon](https://img.shields.io/badge/Sycon-1.2.0-0bf57a.svg)](#)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-blue.svg)](#)
[![Docs](https://img.shields.io/badge/SwaggerUI-success.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](#)

Ce guide explique comment **s’authentifier**, **explorer la documentation Swagger**, **lister vos équipements** et **récupérer des données brutes**.

**Swagger** : <https://hello-sycon.github.io/sycon-api/>  
**URL API** : <https://cloud.sycon.io>  
**Spécification API 1.2.0** : `docs/v1.2.0/sycon-cloud-api`.    

---

## 1) Prérequis
- Un compte client Sycon actif (identifiants fournis par Sycon).
- Accès HTTPS sortant (443).
- Navigateur moderne pour Swagger UI (ou votre outil habituel : Postman, Insomnia, etc.).

---

## 2) Authentification (JWT + Renew)

L’API utilise un **jeton JWT** transmis dans l’en-tête `Authorization` et un jeton **Renew** pour renouveler le JWT sans ressaisir vos identifiants.

**Étapes :**
1. **Login** (`POST /auth/login`) avec vos identifiants.  
   • En cas de succès (`200`), la réponse ne contient **pas** de corps JSON, mais **deux en‑têtes** :  
   `Authorization: Bearer <JWT>` et `Renew: <RENEW_TOKEN>`.
2. **Appeler l’API** en ajoutant `Authorization: Bearer <JWT>` à chaque requête.
3. **Vérifier** votre JWT à tout moment via `GET /auth/check` (retour `200` si valide, `403` sinon).
4. **Renouveler** le JWT via `GET /auth/renew` en envoyant l’en‑tête `Renew: <RENEW_TOKEN>` ; un **nouveau** `Authorization` est renvoyé.

**Bonnes pratiques :**
- Conservez `Renew` de manière sécurisée et **renouvelez avant** l’expiration du JWT.
- Ne partagez jamais vos jetons ni ne les commitez dans un dépôt.

---

## 3) Utiliser Swagger UI (pas à pas)

1. Ouvrez : <https://hello-sycon.github.io/sycon-api-production/>.
2. Cliquez **Authorize** et collez votre valeur `Bearer <JWT>` dans le champ prévu.
3. Utilisez la **recherche** pour trouver un endpoint par nom ou par tag (« API auth », « Data API »).
4. Dépliez un endpoint, cliquez **Try it out**, renseignez les paramètres, puis **Execute**.
5. Consultez le **Request URL**, les **en‑têtes**, et la **réponse** (corps + codes).

> Astuce : Servez‑vous d’un device/field réel récupéré via `/api/devices` pour vos essais.

---

## 4) Parcours type

### A) Lister vos appareils
- Endpoint : `GET /api/devices`
- Résultat : liste des devices rattachés à votre client.  
  Les champs `fields` et `externalSensorIds` reflètent ce qui a été mesuré **sur les 7 derniers jours** (leur absence n’exclut pas des historiques plus anciens).

### B) Récupérer des données brutes capteur
- Endpoint : `GET /api/devices/{deviceId}/{field}/data/raw`
- Paramètres **path** :
  - `deviceId` *(int64, requis)* — identifiant du device.
  - `field` *(enum, requis)* — type de mesure (voir la liste complète dans l’OpenAPI / Swagger).
- Paramètres **query** :

  | Nom               | Type     | Obligatoire | Règles / Exemple                                  |
  |-------------------|----------|-------------|----------------------------------------------------|
  | `start`           | string   | oui         | Instant **UTC** ISO‑8601, ex. `2025-09-22T00:00:00Z` |
  | `end`             | string   | oui         | Instant **UTC** ISO‑8601                            |
  | `headLimit`       | int ≤10000 | au moins 1/2 | Garde les **N premiers** points depuis `start`       |
  | `tailLimit`       | int ≤10000 | au moins 1/2 | Garde les **N derniers** points jusqu’à `end`        |
  | `externalSensorId`| string   | non         | Filtre sur un capteur **externe** précis            |

  > **Règle** : fournir **au moins** `headLimit` **ou** `tailLimit`. Si la fenêtre contient plus de N points, l’API tronque selon l’option choisie.

- Réponse (résumé) :  
  • métadonnées : `deviceId`, `field`, `externalSensorId` (optionnel), `firstTimestamp`, `lastTimestamp`, `count`  
  • données : `dataPoints[]` (chaque point contient `time` (ISO‑8601) et `value` ou `textValue`)

### C) Paginer par fenêtres (recommandé)
- Enchaînez plusieurs appels en découpant votre période (ex. tranches d’1 h).  
- Utilisez `firstTimestamp` / `lastTimestamp` pour avancer sans chevauchement.

---

## 5) Codes d’erreur & Dépannage

**Codes fréquents :**
- `401` — JWT manquant/invalide.
- `403` — Accès refusé (droits/périmètre) ou `Renew` invalide/expiré.
- `404` — Device introuvable.
- `400` — Paramètres invalides (dates, limites manquantes, formats).
- `502` — Erreur lors de l’interrogation des données en backend.

**Checklist rapide :**
1. L’en‑tête `Authorization` commence par **`Bearer `** et le JWT est **valide** (`/auth/check`).
2. `start < end` et vos dates sont au format **ISO‑8601 UTC** (suffixe `Z`).
3. Vous fournissez **`headLimit` ou `tailLimit`** (≤ 10000).
4. Le `deviceId` vous appartient (visible dans `/api/devices`).
5. Le `field` existe pour votre device (il peut ne pas apparaître si aucune mesure récente, mais rester interrogeable si de l’historique existe).

---

## 6) Bonnes pratiques d’intégration

- **UTC partout** : sérialisez vos timestamps avec le suffixe `Z`.
- **Fenêtrage** : préférez des fenêtres limitées (ex. 1 h) plutôt qu’un très large intervalle.
- **Renouvellement proactif** : anticipez l’expiration de votre JWT avec `/auth/renew`.
- **Résilience** : en cas de `502`, appliquez un backoff exponentiel.
- **Sécurité** : ne divulguez jamais `Authorization`/`Renew` (pas de commit, pas de tickets publics).

---

## 7) Support

- Site : <https://www.sycon.fr/>
- Contact : <hello@sycon.fr>
