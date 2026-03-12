# generar_dashboard.py
# ══════════════════════════════════════════════════════════════════
#  Lee el Excel + dashboard_template.html -> genera index.html
#
#  ARCHIVOS NECESARIOS EN LA MISMA CARPETA:
#    - generar_dashboard.py    (este script)
#    - dashboard_template.html (la plantilla HTML — el otro archivo)
#
#  USO:
#    python generar_dashboard.py
#
#  Resultado: index.html  (subelo a GitHub Pages)
# ══════════════════════════════════════════════════════════════════

from pathlib import Path
import pandas as pd
import json
import os
import time
from datetime import datetime
import traceback
import openpyxl

# ── CONFIGURACION ─────────────────────────────────────────────────
RUTA_EXCEL = os.environ.get(
    "RUTA_EXCEL",
    r"C:\Users\RMosquera\OneDrive - CORRECOL\CLIENTES SEGUROS MASIVOS\AGRARIO\RETURNS\ORIGINAL DASHBOARD DEVOLUCIÓN.xlsx"
)
NOMBRE_TABLA_ESPERADO = "Extructura"

CARPETA        = Path(__file__).parent
TEMPLATE_HTML  = CARPETA / "dashboard_template.html"
ARCHIVO_SALIDA = CARPETA / "index.html"

# Marcador que existe en el template y que se reemplaza con los datos
MARCADOR = "__DATOS_JSON__"

COLUMNAS_MAPEO = {
    "fecha":       ["Fecha_de_radicacio_solicitud", "Fecha", "Fecha Radicacion",
                    "FechaSolicitud", "fecha_radicacion", "Fecha_Radicacion", "FECHA"],
    "aseguradora": ["Aseguradora", "Insurance", "Compania", "Aseguradora1", "ASEGURADORA"],
    "estado":      ["Estado_Devolucion", "Estado", "Estado Devolucion", "Status", "ESTADO"],
    "valor":       ["Valor_a_Devolver", "Valor Devolver", "Monto Pendiente",
                    "Valor_a_devolver", "VALOR", "Valor"],
    "monto":       ["Monto_Devolucion", "Monto Pagado", "Valor Pagado",
                    "Monto_Devolucion", "MONTO", "Monto"]
}

ESTADOS_PENDIENTE = ["SOLICITUD"]
ESTADOS_RECHAZADO = ["RECHAZADO", "RECHAZADO-CUENTA INACTIVA BLOQUEADA"]
ESTADOS_PAGADO    = ["REALIZADO", "CONFIRMADA"]

ORDEN_MESES = ["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"]
MESES_ES    = {1:"ENE",2:"FEB",3:"MAR",4:"ABR",5:"MAY",6:"JUN",
               7:"JUL",8:"AGO",9:"SEP",10:"OCT",11:"NOV",12:"DIC"}

UNIFICAR_ASEG = {
    "COLMENA SEGUROS DE VIDA":   "COLMENA",
    "COLMENA SEGUROS GENERALES": "COLMENA",
    "COLMENA SEGUROS":           "COLMENA",
}

# ── HELPERS ───────────────────────────────────────────────────────
def encontrar_columna(df_columns, posibles):
    lower = {str(c).strip().lower(): c for c in df_columns}
    for n in posibles:
        if n.strip().lower() in lower:
            return lower[n.strip().lower()]
    return None

# ── LEER Y PROCESAR EXCEL ─────────────────────────────────────────
def procesar_excel():
    t0 = time.time()
    print(f"Leyendo: {RUTA_EXCEL}")
    ruta = Path(RUTA_EXCEL)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontro: {RUTA_EXCEL}")

    # Detectar hoja
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    hojas = {}
    for h in wb.sheetnames:
        ws = wb[h]
        headers = [str(c.value).strip() for c in next(ws.rows, []) if c.value]
        hojas[h] = headers
    wb.close()

    if NOMBRE_TABLA_ESPERADO in hojas:
        nombre_hoja = NOMBRE_TABLA_ESPERADO
        print(f"OK Hoja: '{nombre_hoja}'")
    elif hojas:
        nombre_hoja = next((h for h in hojas if len(hojas[h]) > 1), list(hojas.keys())[0])
        print(f"AVISO: Usando hoja alternativa: '{nombre_hoja}'")
    else:
        raise ValueError("No se encontraron hojas validas en el Excel")

    df_raw = pd.read_excel(ruta, sheet_name=nombre_hoja, engine="openpyxl")
    print(f"OK {len(df_raw):,} filas x {len(df_raw.columns)} columnas")

    # Mapear columnas
    col_map = {}
    for clave, posibles in COLUMNAS_MAPEO.items():
        found = encontrar_columna(df_raw.columns, posibles)
        if not found:
            raise ValueError(
                f"Columna '{clave}' no encontrada. "
                f"Disponibles: {list(df_raw.columns)[:20]}"
            )
        col_map[clave] = found
        print(f"   OK '{clave}' -> '{found}'")

    df = df_raw[[col_map[k] for k in col_map]].copy()
    df.rename(columns={v: k for k, v in col_map.items()}, inplace=True)

    # Limpiar tipos
    df["fecha"]       = pd.to_datetime(df["fecha"], errors="coerce")
    df["aseguradora"] = df["aseguradora"].astype(str).str.strip().str.upper().replace(UNIFICAR_ASEG)
    df["estado"]      = df["estado"].astype(str).str.strip().str.upper()
    df["valor"]       = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    df["monto"]       = pd.to_numeric(df["monto"], errors="coerce").fillna(0)

    antes = len(df)
    df.dropna(subset=["fecha"], inplace=True)
    descartadas = antes - len(df)
    if descartadas:
        print(f"AVISO: {descartadas} filas descartadas por fecha invalida")

    df["_mes_num"]  = df["fecha"].dt.month
    df["_anio"]     = df["fecha"].dt.year
    df["_mes_str"]  = df["_mes_num"].map(MESES_ES)
    df["_anio_mes"] = df["_anio"].astype(str) + "-" + df["_mes_str"]

    est_pend = [e.upper() for e in ESTADOS_PENDIENTE]
    est_rech = [e.upper() for e in ESTADOS_RECHAZADO]
    est_pag  = [e.upper() for e in ESTADOS_PAGADO]

    df_pend = df[df["estado"].isin(est_pend)]
    df_rech = df[df["estado"].isin(est_rech)]
    df_pag  = df[df["estado"].isin(est_pag)]

    print(f"   Pendientes: {len(df_pend):,} | Rechazados: {len(df_rech):,} | Pagados: {len(df_pag):,}")

    todos_periodos = sorted(
        df["_anio_mes"].unique(),
        key=lambda x: (
            int(x.split("-")[0]),
            ORDEN_MESES.index(x.split("-")[1]) if x.split("-")[1] in ORDEN_MESES else 99
        )
    )

    def agrupar_monto(subdf, col_suma, periodos):
        g = subdf.groupby("_anio_mes")[col_suma].sum().reindex(periodos, fill_value=0)
        return {p: round(float(g[p])) for p in periodos}

    def agrupar_cant(subdf, periodos):
        g = subdf.groupby("_anio_mes").size().reindex(periodos, fill_value=0)
        return {p: int(g[p]) for p in periodos}

    aseguradoras = sorted(df["aseguradora"].dropna().unique())

    resultado = {
        "_meta": {
            "periodos":     todos_periodos,
            "aseguradoras": list(aseguradoras),
            "generado":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hoja_usada":   nombre_hoja,
        }
    }

    for aseg in aseguradoras:
        dp = df_pend[df_pend["aseguradora"] == aseg]
        dr = df_rech[df_rech["aseguradora"] == aseg]
        da = df_pag[df_pag["aseguradora"] == aseg]
        resultado[aseg] = {
            "pendientes": {
                "montos":     agrupar_monto(dp, "valor", todos_periodos),
                "cantidades": agrupar_cant(dp, todos_periodos)
            },
            "rechazados": {
                "montos":     agrupar_monto(dr, "valor", todos_periodos),
                "cantidades": agrupar_cant(dr, todos_periodos)
            },
            "pagados": {
                "montos":     agrupar_monto(da, "monto", todos_periodos),
                "cantidades": agrupar_cant(da, todos_periodos)
            },
        }

    elapsed = time.time() - t0
    print(f"OK Procesado en {elapsed:.1f}s | {len(aseguradoras)} aseguradoras | {len(todos_periodos)} periodos")
    print(f"   Aseguradoras: {list(aseguradoras)}")
    print(f"   Periodos:     {todos_periodos}")
    return resultado

# ── MAIN ──────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  GENERADOR DASHBOARD ESTATICO")
    print("=" * 60)

    # Verificar que existe la plantilla
    if not TEMPLATE_HTML.exists():
        raise FileNotFoundError(
            f"No se encontro la plantilla: {TEMPLATE_HTML}\n\n"
            f"Asegurate de tener estos dos archivos en la misma carpeta:\n"
            f"  - generar_dashboard.py\n"
            f"  - dashboard_template.html"
        )

    # Procesar Excel y generar JSON
    datos = procesar_excel()
    datos_json = json.dumps(datos, ensure_ascii=False, separators=(',', ':'))

    # Leer plantilla e inyectar datos
    print(f"Leyendo plantilla: {TEMPLATE_HTML.name}")
    template = TEMPLATE_HTML.read_text(encoding='utf-8')

    if MARCADOR not in template:
        raise ValueError(
            f"El marcador '{MARCADOR}' no se encontro en el template.\n"
            f"Verifica que dashboard_template.html tenga esta linea en el JS:\n"
            f"  const RAW_DATA = {MARCADOR};"
        )

    html_final = template.replace(MARCADOR, datos_json)

    # Guardar resultado
    ARCHIVO_SALIDA.write_text(html_final, encoding='utf-8')
    size_kb = ARCHIVO_SALIDA.stat().st_size / 1024

    print("=" * 60)
    print(f"ARCHIVO GENERADO: {ARCHIVO_SALIDA.name}")
    print(f"Tamanyo: {size_kb:.0f} KB")
    print()
    print("PROXIMOS PASOS - GitHub Pages (GRATIS):")
    print()
    print("  1. Ve a https://github.com/new")
    print('     Crea un repositorio PUBLICO llamado: dashboard-aseguradoras')
    print()
    print("  2. Sube el archivo index.html al repositorio")
    print()
    print("  3. Settings -> Pages -> Source: main -> / (root) -> Save")
    print()
    print("  4. Tu link publico sera:")
    print("     https://TU_USUARIO.github.io/dashboard-aseguradoras")
    print()
    print("  Para actualizar: vuelve a correr este script y sube el nuevo index.html")
    print("=" * 60)
    input("\nPresiona Enter para cerrar...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        traceback.print_exc()
        input("\nPresiona Enter para cerrar...")
