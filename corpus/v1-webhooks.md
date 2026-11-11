---
id: v1-webhooks
title: v1 webhooks
version: v1
---

Create a webhook endpoint with POST /v1/webhook_endpoints. The body fields are url (required) and events (array, required). The event names are invoice.paid, invoice.opened, and customer.created. Northline signs the raw body and sends the hex digest in the header Northline-Signature. The digest is HMAC-SHA256, using the endpoint signing secret.

The signing secret is shown once at creation and is not published in these docs. Rotate it with POST /v1/webhook_endpoints/{id}/rotate_secret. Delivery timeout is 10 seconds. Failed deliveries retry 3 times.

A v1 endpoint does not emit the newer settled or issued event names.
