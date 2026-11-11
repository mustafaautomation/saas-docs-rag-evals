---
id: v1-invoices
title: v1 invoices
version: v1
---

Create a draft invoice with POST /v1/invoices. The body fields are customer (customer id, required), currency (optional, default usd), and line_items (array of description and amount_cents). The status values are draft, open, paid, and void. Move a draft to open with POST /v1/invoices/{id}/finalize. Fetch one invoice with GET /v1/invoices/{id}.

amount_cents is an integer number of cents. A collected v1 invoice uses the status paid.
