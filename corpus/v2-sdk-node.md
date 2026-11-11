---
id: v2-sdk-node
title: v2 Node SDK
version: v2
---

The v2 Node SDK exports NorthlineClient. The constructor reads NORTHLINE_API_KEY:

import { NorthlineClient } from "@northline/sdk";
const client = new NorthlineClient();
const customer = await client.customers.create({ name: "Ada Lovelace", email: "ada@example.com", account_ref: "acct_42" });

v2 Node resources are client.customers, client.invoices, client.usageRecords, and client.meters.
