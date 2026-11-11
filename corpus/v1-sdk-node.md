---
id: v1-sdk-node
title: v1 Node SDK
version: v1
---

The v1 Node SDK constructs a client from the key and calls a resource method:

import Northline from "@northline/sdk";
const northline = new Northline(process.env.NORTHLINE_API_KEY);
const customer = await northline.customers.create({ name: "Ada Lovelace", email: "ada@example.com", external_id: "acct_42" });

v1 Node resources are customers, invoices, and usageRecords. There is no meters resource on the v1 client.
