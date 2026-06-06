"""
reset_db.py — Script de Mantenimiento / Data Governance
=======================================================
Propósito: Eliminar registros marcados como 'Error_IA' en la
           tabla 'eventos_acceso' de la base de datos
           'smart_gate.db', para mantener la integridad de
           la infraestructura de producción del sistema Smart-Gate.

Auditoría: MLOps & Data Governance
Fecha:     29 de mayo de 2026
"""

import sqlite3
import sys

DB_PATH = "smart_gate.db"
TABLA = "eventos_acceso"
MARCA = "Error_IA"


def limpiar_error_ia(dry_run: bool = False) -> int:
    """
    Conecta a la base de datos y elimina los registros cuyo
    campo 'estado' sea exactamente 'Error_IA'.

    Parámetros
    ----------
    dry_run : bool
        Si es True, solo cuenta los registros sin eliminarlos.

    Retorna
    -------
    int
        Cantidad de registros afectados (eliminados o
        encontrados en dry-run).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Verificar que la tabla existe
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLA,)
    )
    if not cursor.fetchone():
        print(f"[ERROR] La tabla '{TABLA}' no existe en {DB_PATH}.")
        conn.close()
        sys.exit(1)

    # 2. Contar registros a eliminar
    cursor.execute(
        f"SELECT COUNT(*) FROM {TABLA} WHERE estado = ?",
        (MARCA,)
    )
    total = cursor.fetchone()[0]
    print(f"[INFO]  Registros encontrados con estado '{MARCA}': {total}")

    if total == 0:
        print("[INFO]  No hay registros por limpiar. Base de datos OK.")
        conn.close()
        return 0

    # 3. Vista previa (opcional)
    if dry_run:
        cursor.execute(
            f"SELECT id, usuario, fecha FROM {TABLA} WHERE estado = ?",
            (MARCA,)
        )
        print("[DRY-RUN] Registros que serían eliminados:")
        for row in cursor.fetchall():
            print(f"         id={row[0]}, usuario={row[1]}, fecha={row[2]}")
        conn.close()
        return total

    # 4. Ejecutar eliminación
    cursor.execute(
        f"DELETE FROM {TABLA} WHERE estado = ?",
        (MARCA,)
    )
    conn.commit()
    eliminados = cursor.rowcount
    conn.close()

    print(f"[OK]     {eliminados} registro(s) eliminado(s) exitosamente.")
    return eliminados


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Limpieza de registros Error_IA en Smart-Gate"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra los registros que se eliminarían (no ejecuta DELETE)"
    )
    args = parser.parse_args()

    print("=" * 55)
    print("  RESET_DB — Limpieza de Infraestructura Smart-Gate")
    print("=" * 55)
    print(f"  Base de datos : {DB_PATH}")
    print(f"  Tabla         : {TABLA}")
    print(f"  Filtro        : estado = '{MARCA}'")
    print("-" * 55)

    if args.dry_run:
        print("  Modo          : DRY-RUN (solo lectura)")
    else:
        print("  Modo          : EJECUCIÓN")
    print("-" * 55)

    total = limpiar_error_ia(dry_run=args.dry_run)

    print("-" * 55)
    if total == 0:
        print("  [OK] La base de datos esta limpia. No se requirio accion.")
    elif args.dry_run:
        print(f"  [AVISO] Se encontraron {total} registro(s). "
              "Ejecute sin --dry-run para eliminarlos.")
    else:
        print(f"  [OK] Operacion completada. {total} registro(s) eliminado(s).")
    print("=" * 55)
