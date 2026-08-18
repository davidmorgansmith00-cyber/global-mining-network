# GMN-EC-05 NPC Market Purchase Flow

## Market System Overview
- Server-authoritative NPC market with fixed-price catalog items from `content/market_catalog.json`
- No client-side balance or stock authority
- Item inventory supports:
  - `unlimited`
  - fixed limited stock
  - limited stock with optional `restock_rate_per_day`

## Purchase Flow (Client → Server → Ledger)
1. Client sends `POST /api/v1/market/purchase` with `session_id`, `item_id`, and `quantity`.
2. Server runs SERIALIZABLE transaction:
   - locks player row (`FOR UPDATE`)
   - validates player balance from credit ledger projection
   - validates item stock state
   - upserts `player_inventory`
   - decrements stock (if limited)
   - inserts purchase ledger entry (`market.purchase.v1`)
3. Server returns receipt and new balance on success, or a deterministic error code on failure.

## API Contract
- `GET /api/v1/market/catalog`
  - returns `market.catalog.v1` with catalog items and current stock state
- `GET /api/v1/market/item/{item_id}`
  - returns `market.item.v1` for one item
- `POST /api/v1/market/purchase`
  - request: `{ "item_id": "...", "quantity": 1 }`
  - success: `{ "success": true, "receipt": {...}, "new_balance": ... }`
  - error: `{ "success": false, "error": "insufficient_balance|out_of_stock|item_not_found|..." }`

## Content Schema
- Schema: `content/schemas/npc-market.schema.json`
- Catalog file: `content/market_catalog.json`
- Rules:
  - `item_id` unique (enforced by server loader)
  - `price` positive decimal
  - `inventory` is `"unlimited"` or positive integer
  - `item_type` in allowed enum
  - optional `unlock_condition` supports `tier >= N`

## Ledger Audit Trail
Purchase entries are recorded in `economy_player_ledger_entries` with:
- `entry_type = market.purchase.v1`
- `item_id`
- `quantity`
- `unit_price`
- `total_cost`
- `amount` negative credit delta

This keeps purchases replayable and auditable while preserving immutable ledger history.
