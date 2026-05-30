# infra/migrations

This folder contains SQL migrations that can be applied to the BuyerOS database.

## Apply

```bash
psql "$DATABASE_URL" -f infra/migrations/0010_buyer_recon.sql
```

## Notes

- All currency amounts are stored as integer cents (HKD cents).
- These migrations are idempotent (`CREATE TABLE IF NOT EXISTS`).
