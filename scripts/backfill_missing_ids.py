"""CLI deliberadamente opt-in para preencher IDs legados ausentes."""

import argparse
import hmac

from modules.id_backfill import backfill_missing_ids


def should_apply(apply, confirmation):
    return bool(apply) and hmac.compare_digest(confirmation, "BACKFILL_IDS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()

    if args.apply and not should_apply(args.apply, args.confirm):
        parser.error("Use --apply --confirm BACKFILL_IDS para gravar.")

    counts = backfill_missing_ids(apply=should_apply(args.apply, args.confirm))
    for name, count in counts.items():
        print(f"{name}: {count} ID(s) ausente(s)")


if __name__ == "__main__":
    main()
