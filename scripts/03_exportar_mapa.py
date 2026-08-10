"""Launch EE exports of the classified maps to GCS. They take a while — launch
them at night (SPEC §10) and check progress at https://code.earthengine.google.com/tasks
or with `earthengine task list`.
"""

import argparse
import datetime

from mapa_cultivos import clasificar, ee_client, exportar
from mapa_cultivos.settings import settings
from mapa_cultivos.zonas import ZONAS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zona", choices=list(ZONAS), help="por defecto, las dos")
    parser.add_argument("--modelo", choices=list(clasificar.MODELOS), help="por defecto, los cuatro")
    parser.add_argument("--corrida", default=datetime.date.today().isoformat())
    args = parser.parse_args()

    ee_client.init()
    zonas_sel = [args.zona] if args.zona else list(ZONAS)
    modelos_sel = [args.modelo] if args.modelo else list(clasificar.MODELOS)

    for zona in zonas_sel:
        for modelo in modelos_sel:
            tarea = exportar.exportar_mapa(zona, settings.mnc_campania, modelo, args.corrida)
            print(f"lanzado: {zona} · {modelo} → tarea {tarea.id}")

    print(
        f"\n{len(zonas_sel) * len(modelos_sel)} exports lanzados a "
        f"gs://{settings.gcs_tiles_bucket}/exports/{args.corrida}/"
    )


if __name__ == "__main__":
    main()
