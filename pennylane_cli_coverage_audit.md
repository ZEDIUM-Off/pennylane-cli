# Audit couverture CLI Pennylane vs OpenAPI

- Source: https://pennylane.readme.io/openapi/accounting.json
- Opérations visibles OpenAPI: 160
- Opérations uniques couvertes par le registry ergonomique: 160/160
- Entrées registry avec aliases ergonomiques: 182
- Commande universelle: `cli-anything-pennylane call OPERATION`
- Escape hatch conservé: `cli-anything-pennylane request METHOD PATH`

## Couverture par groupe

- `bank_accounts`: 3/3
- `bank_establishments`: 1/1
- `billing_subscriptions`: 6/6
- `categories`: 5/5
- `category_groups`: 2/2
- `changelogs`: 7/7
- `commercial_documents`: 6/6
- `customer_invoice_templates`: 1/1
- `customer_invoices`: 23/23
- `customers`: 11/11
- `e-invoices`: 1/1
- `exports`: 6/6
- `file_attachments`: 1/1
- `fiscal_years`: 1/1
- `journals`: 3/3
- `ledger_accounts`: 4/4
- `ledger_attachments`: 1/1
- `ledger_entries`: 5/5
- `ledger_entry_lines`: 7/7
- `mandates`: 14/14
- `pa_registrations`: 1/1
- `products`: 4/4
- `purchase_requests`: 3/3
- `quotes`: 11/11
- `supplier_invoices`: 14/14
- `suppliers`: 6/6
- `transactions`: 11/11
- `trial_balance`: 1/1
- `users`: 1/1

## Note

Cet audit a été actualisé après régénération du registry depuis l'OpenAPI Pennylane courante. L'API visible est passée de 159 à 160 opérations uniques depuis le précédent audit.
