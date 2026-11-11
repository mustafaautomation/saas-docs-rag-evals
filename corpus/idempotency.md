---
id: idempotency
title: Idempotency
version: shared
---

Send the Idempotency-Key header on create requests that must not run twice. Northline stores the key for 24 hours. Replaying the same key with the same body returns the original response. Replaying the same key with a different body returns error code idempotency_conflict.

Use a new key when the request body changes. Keys are opaque strings chosen by the client. The docs do not assign a key for you.
