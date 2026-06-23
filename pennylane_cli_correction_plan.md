# Plan de correction — couverture routes Pennylane CLI

## Constat

Source de vérité: `https://pennylane.readme.io/openapi/accounting.json`, découverte depuis `https://pennylane.readme.io/llms.txt`.

- OpenAPI visible: 159 opérations non-hidden.
- CLI actuel: `request METHOD PATH` peut appeler toutes les routes en mode raw.
- Registry ergonomique `resource`: seulement 24 opérations visibles couvertes exactement sur 159.
- Limitations fonctionnelles: `resource` ne supporte que `GET` et `POST`; pas de `PUT`/`DELETE`; pas de multipart; plusieurs chemins enregistrés ne correspondent plus aux chemins OpenAPI 2026 (`exports/fec` vs `exports/fecs`, etc.).

Audit détaillé: `pennylane_cli_coverage_audit.md`.

## Objectif

Atteindre une couverture ergonomique complète des routes visibles OpenAPI, tout en conservant `request` comme escape hatch.

## Stratégie proposée

### 1. Remplacer le registry manuel par un registry dérivé OpenAPI

Créer un module `core/openapi_registry.py` qui expose une structure normalisée:

```python
{
  "operation_id": "getTransactions",
  "name": "transactions.list",
  "method": "GET",
  "path_template": "/api/external/v2/transactions",
  "summary": "List transactions",
  "tags": ["Transactions"],
  "content_types": ["application/json"]
}
```

Le registry peut être généré offline à partir du JSON OpenAPI et commité dans `core/generated_endpoints.py` pour éviter une dépendance réseau à runtime.

### 2. Généraliser les commandes `resource`

Ajouter des commandes génériques:

- `resource call NAME_OR_OPERATION_ID`
  - options: `--method`, `--id`, `--path-param key=value`, `--param key=value`, `--data`, `--data-file`, `--file field=path`, `--dry-run`.
- garder aliases existants:
  - `resource get` -> `resource call ... --method GET`
  - `resource post` -> `resource call ... --method POST`
- ajouter:
  - `resource put`
  - `resource delete`

### 3. Supporter les templates de chemin

Mapper les placeholders OpenAPI:

- `/customer_invoices/{customer_invoice_id}/matched_transactions/{id}`
- `/ledger_entry_lines/{ledger_entry_line_id}/categories`

via `--path-param customer_invoice_id=... --path-param id=...`.

Option ergonomique: garder `--id` comme raccourci si le chemin contient `{id}`.

### 4. Ajouter le multipart/form-data

Nécessaire pour:

- `/file_attachments`
- appendices de devis/factures/documents commerciaux
- imports e-invoices éventuels

Implémenter dans `pennylane_backend.py` une fonction `request_multipart(...)`, sans stocker les fichiers ni les tokens.

### 5. Corriger les endpoints obsolètes existants

Aligner le registry actuel sur OpenAPI:

- `exports/fec` -> `/exports/fecs`
- `exports/general_ledger` -> `/exports/general_ledgers`
- `exports/analytical_general_ledger` -> `/exports/analytical_general_ledgers`
- `company_fiscal_years` -> `/fiscal_years`

### 6. Tests

Ajouter tests unitaires/E2E avec serveur local pour:

- résolution des chemins templates;
- `GET`, `POST`, `PUT`, `DELETE`;
- query params + body JSON;
- multipart upload;
- compatibilité des commandes existantes;
- test de couverture: toutes opérations OpenAPI visibles ont une entrée registry.

### 7. Documentation

Mettre à jour:

- `README.md`
- `skills/SKILL.md`
- exemples d'usage pour transactions, justificatifs, supplier invoices, matching.

## Phasage recommandé

1. **Rapide / safe**: corriger endpoints obsolètes + ajouter `resource put/delete` + path params.
2. **Complet**: générateur OpenAPI + registry complet.
3. **Fichiers**: multipart + commandes `file upload` / `appendix upload`.
4. **UX métier**: commandes haut niveau `transactions unmatched`, `supplier-invoice import-with-file`, `match`.
