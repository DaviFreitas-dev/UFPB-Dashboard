"""CLI de plano revisável para preencher IDs legados ausentes."""

import argparse
import hmac
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.id_backfill import (
    apply_backfill_plan,
    build_backfill_plan,
)


CONFIRMATION = "BACKFILL_IDS"


def render_plan(plan):
    lines = [f"Plano NEXO de IDs v{plan['version']} (dry-run; nenhuma escrita)"]
    total = 0
    for worksheet in plan["worksheets"]:
        name = worksheet["worksheet"]
        updates = worksheet["updates"]
        if worksheet["state"] == "missing":
            lines.append(f"{name}: ausente")
            continue
        if not updates:
            lines.append(f"{name}: presente, sem IDs pendentes")
            continue
        lines.append(f"{name}: presente, {len(updates)} ID(s) pendente(s)")
        total += len(updates)
        for update in updates:
            lines.append(
                "  "
                f"linha {update['row']} | célula {update['cell']} | "
                f"UUID {update['uuid']}"
            )
    lines.append(f"Total: {total} ID(s) pendente(s)")
    return "\n".join(lines)


def _read_plan(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"Não foi possível ler o arquivo de plano: {path}"
        ) from error


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Gera um dry-run revisável ou aplica exatamente um arquivo de plano."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--plan-out",
        type=Path,
        help="salva o plano JSON v1 que deverá ser revisado antes do apply",
    )
    mode.add_argument(
        "--apply-plan",
        type=Path,
        help="aplica exatamente o arquivo de plano revisado",
    )
    parser.add_argument("--confirm", default="")
    args = parser.parse_args(argv)

    if args.apply_plan is not None:
        if not hmac.compare_digest(args.confirm, CONFIRMATION):
            parser.error(
                "Use --apply-plan ARQUIVO --confirm BACKFILL_IDS para gravar."
            )
        plan = _read_plan(args.apply_plan)
        counts = apply_backfill_plan(plan)
        for name, count in counts.items():
            print(f"{name}: {count} ID(s) aplicado(s)")
        return 0

    if args.confirm:
        parser.error("--confirm só pode ser usado junto de --apply-plan.")

    plan = build_backfill_plan()
    print(render_plan(plan))
    if args.plan_out is not None:
        args.plan_out.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Plano salvo em: {args.plan_out}")
    else:
        print("Plano não salvo; use --plan-out ARQUIVO para persistir a revisão.")
    return 0


if __name__ == "__main__":
    main()
