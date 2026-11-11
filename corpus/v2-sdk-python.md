---
id: v2-sdk-python
title: v2 Python SDK
version: v2
---

The v2 Python SDK uses a client object. The constructor reads NORTHLINE_API_KEY:

from northline import NorthlineClient
client = NorthlineClient()
customer = client.customers.create(name="Ada Lovelace", email="ada@example.com", account_ref="acct_42", tax_id="EU123")

v2 Python resources are client.customers, client.invoices, client.usage_records, and client.meters. usage_records.create takes meter_id and a decimal string quantity.
