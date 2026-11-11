---
id: v2-invoices
title: v2 invoices
version: v2
---

Create a draft invoice with POST /v2/invoices. The body fields are customer_id (required), currency (required, ISO code), and lines (array of description and amount, where amount is a decimal string). The status values are draft, issued, settled, and void. Move a draft to issued with POST /v2/invoices/{invoice_id}/issue. Fetch one invoice with GET /v2/invoices/{invoice_id}.

A settled invoice has been collected. amount is a decimal string of major units, not an integer count of cents.
