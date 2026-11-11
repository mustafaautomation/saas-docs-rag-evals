---
id: v2-webhooks
title: v2 webhooks
version: v2
---

Create a webhook endpoint with POST /v2/webhook_endpoints. The body fields are url (required) and events (required). The event names are invoice.settled, invoice.issued, customer.created, and usage.recorded. Northline signs a timestamp, a dot, and the raw body, and sends the hex digest in the header Northline-Signature-256. The digest is HMAC-SHA256. Timestamp tolerance is 5 minutes.

Send a test event with POST /v2/webhook_endpoints/{endpoint_id}/ping. The signing secret is shown once and is not published in these docs. Failed deliveries retry 6 times over 24 hours.
