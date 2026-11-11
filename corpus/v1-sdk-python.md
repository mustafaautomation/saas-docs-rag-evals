---
id: v1-sdk-python
title: v1 Python SDK
version: v1
---

The v1 Python SDK uses module-level resources. Set the key from the environment, then call the class method:

import northline
northline.api_key = os.environ["NORTHLINE_API_KEY"]
customer = northline.Customer.create(name="Ada Lovelace", email="ada@example.com", external_id="acct_42")

The v1 Python classes are northline.Customer, northline.Invoice, and northline.UsageRecord. UsageRecord.create takes metric and an integer quantity.
