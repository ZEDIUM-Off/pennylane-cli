# Plan d'implémentation complète des ressources Pennylane CLI

## But

Couvrir toutes les opérations visibles de l'OpenAPI Pennylane v2 avec un CLI moins verbeux, extensible et maintenable.

Objectifs concrets:

- 159 opérations OpenAPI visibles couvertes par des commandes ergonomiques.
- Zéro duplication importante entre ressources.
- Support complet: `GET`, `POST`, `PUT`, `DELETE`, path params, query params, JSON body, multipart upload.
- Conserver `request METHOD PATH` comme escape hatch.
- Garder compatibilité avec les commandes actuelles `resource get/post`.

## Architecture proposée

### 1. Couche transport HTTP

Fichier: `cli_anything/pennylane/core/http.py`

Classes:

```python
class PennylaneClient:
    def request_json(self, method, path, *, query=None, body=None) -> APIResponse: ...
    def request_multipart(self, method, path, *, query=None, files=None, fields=None) -> APIResponse: ...
```

Responsabilités:

- token/base_url/session;
- auth header;
- rate limit parsing;
- retry 429;
- JSON parsing;
- multipart boundary;
- erreurs normalisées.

### 2. Modèle OpenAPI interne

Fichier: `cli_anything/pennylane/core/operations.py`

```python
@dataclass(frozen=True)
class Operation:
    name: str                 # e.g. transactions.list
    operation_id: str          # e.g. getTransactions
    method: str
    path_template: str
    summary: str
    tags: tuple[str, ...]
    query_params: tuple[str, ...]
    path_params: tuple[str, ...]
    request_content_types: tuple[str, ...]
    deprecated: bool = False
```

```python
class OperationRegistry:
    def list(self, tag=None) -> list[Operation]: ...
    def get(self, name_or_operation_id) -> Operation: ...
    def by_tag(self, tag) -> list[Operation]: ...
```

Le registry final doit être généré depuis OpenAPI puis commité en Python pour ne pas dépendre du réseau à runtime.

### 3. Générateur OpenAPI offline

Fichier: `scripts/generate_openapi_registry.py`

Entrée:

- `https://pennylane.readme.io/openapi/accounting.json`

Sortie:

- `cli_anything/pennylane/core/generated_operations.py`

Règles de nommage:

| OpenAPI tag/path | Nom CLI |
|---|---|
| `GET /transactions` | `transactions.list` |
| `GET /transactions/{id}` | `transactions.get` |
| `PUT /transactions/{id}` | `transactions.update` |
| `PUT /transactions/{id}/categories` | `transactions.categories.update` |
| `POST /customer_invoices/{id}/send_by_email` | `customer-invoices.send-by-email` |

La génération doit aussi produire un rapport de collision si deux routes donnent le même nom.

### 4. Classes abstraites de ressources

Fichier: `cli_anything/pennylane/resources/base.py`

```python
class BaseResource:
    resource_name: str
    path: str

    def __init__(self, client: PennylaneClient): ...
    def list(self, **query): ...
    def get(self, id, **query): ...
    def create(self, data, **query): ...
    def update(self, id, data, **query): ...
    def delete(self, id, **query): ...
```

Mixins réutilisables:

```python
class CategorisableMixin:
    def list_categories(self, id): ...
    def update_categories(self, id, categories): ...

class AppendicesMixin:
    def list_appendices(self, id): ...
    def upload_appendix(self, id, file_path, filename=None): ...

class InvoiceLinesMixin:
    def list_invoice_lines(self, id): ...
    def list_invoice_line_sections(self, id): ...

class PaymentsMixin:
    def list_payments(self, id): ...

class MatchedTransactionsMixin:
    def list_matched_transactions(self, id): ...
    def match_transaction(self, id, transaction_id, amount=None): ...
    def unmatch_transaction(self, id, match_id): ...

class SendByEmailMixin:
    def send_by_email(self, id, data=None): ...
```

Exemples de ressources concrètes:

```python
class TransactionsResource(BaseResource, CategorisableMixin):
    resource_name = "transactions"
    path = "/api/external/v2/transactions"

    def matched_invoices(self, transaction_id): ...

class SupplierInvoicesResource(
    BaseResource,
    CategorisableMixin,
    InvoiceLinesMixin,
    PaymentsMixin,
    MatchedTransactionsMixin,
):
    resource_name = "supplier-invoices"
    path = "/api/external/v2/supplier_invoices"

    def import_with_file(self, data): ...
    def validate_accounting(self, id): ...
    def update_payment_status(self, id, data): ...
```

But: les commandes métier peuvent appeler ces classes plutôt que manipuler des strings de paths partout.

### 5. Commandes CLI moins verbeuses

#### Commande générique universelle

```bash
cli-anything-pennylane call transactions.list --param limit=20
cli-anything-pennylane call transactions.get --id 123
cli-anything-pennylane call supplier-invoices.update --id 456 --data '{...}'
cli-anything-pennylane call customer-invoices.send-by-email --id 789 --data '{...}'
```

Options standard:

- `--id VALUE` raccourci pour `{id}`;
- `--path-param key=value` pour autres placeholders;
- `--param key=value` pour query;
- `--data JSON` / `--data-file FILE`;
- `--file field=path` pour multipart;
- `--field key=value` pour champs multipart;
- `--dry-run`.

#### Commandes alias ressources

Moins verbeux pour les cas courants:

```bash
cli-anything-pennylane transactions list --limit 100
cli-anything-pennylane transactions get 123
cli-anything-pennylane transactions categories update 123 --data-file categories.json

cli-anything-pennylane suppliers list
cli-anything-pennylane supplier-invoices import --data-file invoice.json
cli-anything-pennylane files upload justificatif.pdf
```

Implémentation: les alias sont générés ou déclarés via les classes Resource, mais délèguent toujours à `OperationRegistry`/`PennylaneClient`.

### 6. Organisation des fichiers

```text
cli_anything/pennylane/
  core/
    http.py
    operations.py
    generated_operations.py
    session.py
    api.py                  # façade compatibilité ancienne API
  resources/
    __init__.py
    base.py
    accounting.py            # journals, ledger_accounts, ledger_entries...
    customers.py
    customer_invoices.py
    suppliers.py
    supplier_invoices.py
    transactions.py
    products.py
    files.py
    exports.py
    mandates.py
  cli/
    __init__.py
    root.py
    call.py
    resource_commands.py
    generated_commands.py    # optionnel
  pennylane_cli.py           # devient thin entrypoint
scripts/
  generate_openapi_registry.py
```

### 7. Couverture par domaine à implémenter

Priorité 1 — coeur utile immédiat:

- `transactions` complet;
- `file_attachments` multipart;
- `supplier_invoices` complet;
- `suppliers` complet;
- `customer_invoices` complet;
- `customers` complet;
- `products` complet.

Priorité 2 — comptabilité:

- `journals`;
- `ledger_accounts`;
- `ledger_entries`;
- `ledger_entry_lines`;
- `categories` / `category_groups`;
- `trial_balance`;
- `fiscal_years`.

Priorité 3 — ventes avancées / exports:

- `quotes`;
- `commercial_documents`;
- `billing_subscriptions`;
- `exports`;
- `customer_invoice_templates`.

Priorité 4 — banque / mandats / divers:

- `bank_accounts`;
- `bank_establishments`;
- `sepa_mandates`;
- `gocardless_mandates`;
- `pro_account`;
- `purchase_requests`;
- `pa_registrations`;
- `changelogs`.

### 8. Tests

#### Tests unitaires

- `OperationRegistry.get()` par nom et operationId;
- résolution de path template;
- parsing `--param`, `--path-param`, `--file`, `--field`;
- JSON body;
- multipart body;
- mapping erreurs.

#### Tests E2E serveur local

- `call transactions.list`;
- `call transactions.get --id 1`;
- `call supplier-invoices.update --id 1 --data ...`;
- `call customer-invoices.delete --id 1`;
- `files upload test.pdf`;
- aliases `transactions list`, `supplier-invoices import`.

#### Test de couverture OpenAPI

Un test doit échouer si une opération visible OpenAPI n'a pas d'entrée registry:

```python
def test_all_visible_openapi_operations_are_registered(): ...
```

### 9. Compatibilité ascendante

Garder ces commandes:

```bash
resource list
resource get ENDPOINT --id ... --subpath ...
resource post ENDPOINT --data ...
request METHOD PATH
```

Mais les faire déléguer à la nouvelle couche:

- `resource list` liste les nouvelles opérations;
- les anciens noms `customer-invoices`, `supplier-invoices`, etc. restent des aliases.

### 10. Étapes d'implémentation

#### Phase A — fondation

1. Créer `Operation`, `OperationRegistry`.
2. Créer générateur OpenAPI.
3. Générer `generated_operations.py`.
4. Ajouter test de couverture.

#### Phase B — transport complet

1. Extraire `PennylaneClient`.
2. Ajouter `request_multipart`.
3. Migrer `raw_call` et `call_endpoint` vers le client.

#### Phase C — commande universelle

1. Ajouter `call`.
2. Ajouter path params.
3. Ajouter `PUT`/`DELETE`.
4. Ajouter multipart.

#### Phase D — classes ressources

1. Implémenter `BaseResource` + mixins.
2. Implémenter les domaines priorité 1.
3. Ajouter aliases CLI courts pour priorité 1.

#### Phase E — couverture complète

1. Implémenter domaines priorité 2/3/4.
2. Ajouter tests spécifiques par domaine.
3. Mettre à jour README/SKILL.

#### Phase F — nettoyage

1. Déprécier progressivement l'ancien registry manuel.
2. Garder mapping d'aliases legacy.
3. Ajouter changelog interne.

## Critères d'acceptation

- `pytest` OK.
- Le test de couverture OpenAPI passe avec 100% des routes visibles enregistrées.
- `cli-anything-pennylane call --help` documente les options universelles.
- `cli-anything-pennylane files upload ./justif.pdf` fonctionne en multipart.
- Les commandes existantes continuent de fonctionner.
- L'audit passe de `24/159` à `159/159` pour le registry ergonomique.
