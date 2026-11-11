---
id: overview
title: Northline API overview
version: shared
---

Northline Labs is a fictional company. The Northline API is a fictional usage-billing API. Software products use it to store customer records, invoices, and metered usage. These pages are synthetic documentation written for a demo. They describe no real vendor and no real customer.

The HTTP API is served at https://api.northline.example. Read the versioning page before you choose a client. Official Python and Node clients are described on the SDK page. Every request is authenticated. Errors use one JSON shape, lists are cursor paginated, and unsafe retries should send an idempotency key.

Northline does not publish API keys, webhook signing secrets, or sample credentials in this documentation. A key is displayed once in the dashboard when it is created.
