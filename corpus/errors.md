---
id: errors
title: Error codes
version: shared
---

Every error body has the same shape: {"error": {"code": "...", "message": "...", "doc_url": "..."}}.

Documented codes:
authentication_failed uses HTTP status 401.
rate_limited uses HTTP status 429.
parameter_unknown uses HTTP status 400 and means the body contains a field the endpoint does not accept.
resource_missing uses HTTP status 404.
idempotency_conflict uses HTTP status 409.

Clients should branch on the code string, not on the message text. Message wording can change between releases.
