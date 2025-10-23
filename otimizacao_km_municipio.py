"""
GTFS -> Shapefiles (COMPLETO) -> Repartição de km e nº de paragens por município
Saída: 1 Excel por Área em C:\VSC\Km_p_municipio
Folhas: 'extension_per_municipality' e 'paragens_pro municipio'

Regras:
- Áreas 1–3: preferir YEAR, mesmo quando YEAR está ZIPADO; se não houver YEAR, usar REF.
- Área 4: forçar REF (pasta/ZIP).
- Criar 'shapefiles' dentro da pasta YEAR/REF escolhida.
- Concelhos.shp e bridges.shp são inputs fixos (variáveis no topo).
"""

import re
import zipfile
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString


# Parâmetros
BASE = Path(r"C:\Users\MargaridaDias\TML\Gestão de Contratos - Documents\General\ISO\1 Análise de Planos")
AREAS = [f"Área {i}" for i in (1, 2, 3, 4)]
OUT_DIR = Path(r"C:\VSC\Km_p_municipio")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Inputs fixos
CONCELHOS_PATH = Path(r"C:\VSC\Km_p_municipio\inputs\Concelhos.shp")
BRIDGES_PATH   = Path(r"C:\VSC\Km_p_municipio\inputs\bridges.shp")

TODAY_TAG = datetime.now().strftime("%Y%m%d")


def log(msg: str) -> None:
    print(msg, flush=True)


# Helpers 
def parse_year_month_from_name(name: str) -> Optional[Tuple[int, int]]:
    m = re.search(r"(20\d{2})[-_ ]?(\d{2})", name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def latest_month_folder_by_name(area_dir: Path) -> Optional[Path]:
    month_dirs = [d for d in area_dir.iterdir() if d.is_dir()]
    if not month_dirs:
        return None
    keyed = [(parse_year_month_from_name(d.name), d) for d in month_dirs]
    keyed = [(k, d) for (k, d) in keyed if k is not None]
    if keyed:
        keyed.sort(key=lambda x: (x[0][0], x[0][1]))
        return keyed[-1][1]
    return max(month_dirs, key=lambda p: p.stat().st_mtime)


def unzip_to(zip_path: Path, target_dir: Path) -> Path:
    if not target_dir.exists():
        log(f"  • A descomprimir: {zip_path.name}")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(target_dir)
    return target_dir


def find_gtfs_candidate(month_dir: Path, force_ref: bool = False) -> Optional[Path]:
    """
    Seleciona YEAR/REF com prioridade correta considerando pastas e ZIPs.
    - force_ref=True (Área 4): prioridade REF > YEAR
    - caso contrário: prioridade YEAR > REF
    """
    cands = []
    for p in month_dir.iterdir():
        name_up = p.name.upper()
        if p.is_dir() and ("YEAR" in name_up or "REF" in name_up):
            tag = "YEAR" if "YEAR" in name_up else "REF"
            cands.append((tag, p, False))
        elif p.suffix.lower() == ".zip" and ("YEAR" in name_up or "REF" in name_up):
            tag = "YEAR" if "YEAR" in name_up else "REF"
            cands.append((tag, p, True))

    if not cands:
        return None

    tag_order = ["REF", "YEAR"] if force_ref else ["YEAR", "REF"]

    for tag in tag_order:
        tag_cands = [(path, is_zip) for (t, path, is_zip) in cands if t == tag]
        if not tag_cands:
            continue
        # último por nome (os teus nomes já codificam a ordem temporal)
        path, is_zip = sorted(tag_cands, key=lambda x: x[0].name)[-1]
        return unzip_to(path, month_dir / path.stem) if is_zip else path

    # fallback
    path, is_zip = sorted([(p, z) for (_, p, z) in cands], key=lambda x: x[0].name)[-1]
    return unzip_to(path, month_dir / path.stem) if is_zip else path


# GTFS to Shapefiles
def build_shapefiles_from_gtfs_complete(gtfs_dir: Path, shp_dir: Path) -> None:
    """Gera TODOS os shapefiles obrigatórios dentro de <GTFS>/shapefiles."""
    log("    - A gerar shapefiles (versão COMPLETA)…")

    # Ler GTFS
    stops_df      = pd.read_csv(gtfs_dir / "stops.txt", dtype=str)
    stop_times_df = pd.read_csv(gtfs_dir / "stop_times.txt", dtype=str)
    shapes_df     = pd.read_csv(gtfs_dir / "shapes.txt", dtype=str)
    trips_df      = pd.read_csv(gtfs_dir / "trips.txt", dtype=str)
    routes_df     = pd.read_csv(gtfs_dir / "routes.txt", dtype=str) if (gtfs_dir / "routes.txt").exists() else pd.DataFrame()

    # Stops
    for c in ("stop_lat", "stop_lon"):
        stops_df[c] = pd.to_numeric(stops_df[c], errors="coerce")
    stops_gdf = gpd.GeoDataFrame(stops_df, geometry=gpd.points_from_xy(stops_df.stop_lon, stops_df.stop_lat), crs="EPSG:4326")
    (shp_dir / "stops.shp").unlink(missing_ok=True)
    stops_gdf.to_file(shp_dir / "stops.shp")

    # Stop_times
    st_merge = stop_times_df.merge(stops_df[["stop_id","stop_lon","stop_lat"]], on="stop_id", how="left")
    for c in ("stop_lat", "stop_lon"):
        st_merge[c] = pd.to_numeric(st_merge[c], errors="coerce")
    st_gdf = gpd.GeoDataFrame(st_merge, geometry=gpd.points_from_xy(st_merge.stop_lon, st_merge.stop_lat), crs="EPSG:4326")

    if "trip_id" in st_gdf.columns:
        if "pattern_id" not in trips_df.columns:
            # inferir pattern_id (ajusta ao teu padrão de trip_id se necessário)
            trips_df["pattern_id"] = trips_df["trip_id"].astype(str).str.split("_").str[:3].str.join("_")
            log("      (Aviso) 'pattern_id' não existia em trips — inferido de trip_id.")
        keep_trips = [c for c in ["trip_id","route_id","shape_id","pattern_id"] if c in trips_df.columns]
        st_gdf = st_gdf.merge(trips_df[keep_trips], on="trip_id", how="left")
        if not routes_df.empty and "route_id" in routes_df.columns:
            keep_rt = [c for c in ["route_id","line_id","line_short_name","line_long_name",
                                   "route_origin","route_destination","route_short_name","route_long_name"]
                       if c in routes_df.columns]
            if keep_rt:
                st_gdf = st_gdf.merge(routes_df[keep_rt], on="route_id", how="left")

    (shp_dir / "stop_times.shp").unlink(missing_ok=True)
    st_gdf.to_file(shp_dir / "stop_times.shp")

    # Shapes_points
    for c in ("shape_pt_lat","shape_pt_lon"):
        shapes_df[c] = pd.to_numeric(shapes_df[c], errors="coerce")
    shp_pts_gdf = gpd.GeoDataFrame(shapes_df, geometry=gpd.points_from_xy(shapes_df.shape_pt_lon, shapes_df.shape_pt_lat), crs="EPSG:4326")

    if "shape_id" in shp_pts_gdf.columns and "shape_id" in trips_df.columns:
        if "pattern_id" not in trips_df.columns:
            trips_df["pattern_id"] = trips_df["trip_id"].astype(str).str.split("_").str[:3].str.join("_")
        shp_pts_gdf = shp_pts_gdf.merge(trips_df.drop_duplicates(subset=["shape_id"])[["shape_id","pattern_id"]],
                                        on="shape_id", how="left")

    (shp_dir / "shapes_points.shp").unlink(missing_ok=True)
    shp_pts_gdf.to_file(shp_dir / "shapes_points.shp")

    # Shapes_lines
    shapes_df["shape_pt_sequence_num"]   = pd.to_numeric(shapes_df.get("shape_pt_sequence"), errors="coerce")
    shapes_df["shape_dist_traveled_num"] = pd.to_numeric(shapes_df.get("shape_dist_traveled"), errors="coerce")
    shapes_df["shape_pt_lat"]            = pd.to_numeric(shapes_df["shape_pt_lat"], errors="coerce")
    shapes_df["shape_pt_lon"]            = pd.to_numeric(shapes_df["shape_pt_lon"], errors="coerce")

    shapes_clean = shapes_df.dropna(subset=["shape_pt_lat", "shape_pt_lon", "shape_pt_sequence_num"]).copy()

    lines = []
    for sid, grp in shapes_clean.groupby("shape_id"):
        if "shape_dist_traveled_num" in grp.columns and grp["shape_dist_traveled_num"].notna().any():
            grp = grp.sort_values(["shape_pt_sequence_num", "shape_dist_traveled_num"], kind="mergesort")
        else:
            grp = grp.sort_values("shape_pt_sequence_num", kind="mergesort")

        coords = list(zip(grp["shape_pt_lon"].to_numpy(), grp["shape_pt_lat"].to_numpy()))
        if len(coords) >= 2:
            lines.append({"shape_id": sid, "geometry": LineString(coords)})

    lines_gdf = gpd.GeoDataFrame(lines, crs="EPSG:4326")

    if "shape_id" in trips_df.columns:
        if "pattern_id" not in trips_df.columns:
            trips_df["pattern_id"] = trips_df["trip_id"].astype(str).str.split("_").str[:3].str.join("_")
        s2p = trips_df.dropna(subset=["shape_id"]).drop_duplicates(subset=["shape_id"])[["shape_id","pattern_id"]]
        lines_gdf = lines_gdf.merge(s2p, on="shape_id", how="left")

    (shp_dir / "shapes_lines.shp").unlink(missing_ok=True)
    lines_gdf.to_file(shp_dir / "shapes_lines.shp")

    # Paragens_percursos
    par_perc = stop_times_df[["trip_id","stop_id","stop_sequence"]].merge(
        trips_df[["trip_id","pattern_id"]], on="trip_id", how="left"
    ).merge(
        stops_df[["stop_id","stop_lon","stop_lat"] + (["stop_name"] if "stop_name" in stops_df.columns else [])],
        on="stop_id", how="left"
    )
    for c in ("stop_lat","stop_lon"):
        par_perc[c] = pd.to_numeric(par_perc[c], errors="coerce")

    cols = ["pattern_id","stop_id","stop_sequence"] + (["stop_name"] if "stop_name" in stops_df.columns else [])
    par_gdf = gpd.GeoDataFrame(par_perc[cols], geometry=gpd.points_from_xy(par_perc.stop_lon, par_perc.stop_lat), crs="EPSG:4326")
    par_gdf = par_gdf.drop_duplicates(subset=["pattern_id","stop_id","stop_sequence"])

    (shp_dir / "paragens_percursos.shp").unlink(missing_ok=True)
    par_gdf.to_file(shp_dir / "paragens_percursos.shp")


# Inputs fixos
def discover_input(path_hint: Path, filename: str) -> Path:
    """
    Se path_hint existir, usa-se. Caso contrário, tenta descobrir automaticamente
    em C:\\VSC\\Km_p_municipio\\inputs e em C:\\VSC\\Km_p_municipio (procura recursiva).
    """
    if path_hint and path_hint.exists():
        return path_hint

    roots = [
        Path(r"C:\VSC\Km_p_municipio\inputs"),
        Path(r"C:\VSC\Km_p_municipio"),
    ]
    for root in roots:
        if root.exists():
            hits = list(root.rglob(filename))
            if hits:
                log(f"    [INFO] '{filename}' encontrado automaticamente em: {hits[0]}")
                return hits[0]
    raise FileNotFoundError(f"Input obrigatório em falta: {path_hint if path_hint else filename}")


def concelho_field_name(cols: List[str]) -> str:
    for c in ["Concelho", "concelho", "Municipio", "Município", "NAME_2", "NAME"]:
        if c in cols:
            return c
    raise KeyError("Campo do concelho não encontrado no Concelhos.shp.")


def calcular_totais(stops_gdf: gpd.GeoDataFrame, lines_gdf: gpd.GeoDataFrame):
    total_stops = stops_gdf.groupby("pattern_id").size().reset_index(name="stop_count")
    tot_ext = (
        lines_gdf.to_crs("EPSG:3857")
        .groupby("pattern_id")
        .apply(lambda df: df.geometry.length.sum() / 1000.0)
        .reset_index(name="total_extension_km")
    )
    return total_stops, tot_ext


def correr_reparticao(shp_dir: Path):
    # localizar inputs fixos (com auto-descoberta)
    conc_path = discover_input(CONCELHOS_PATH, "Concelhos.shp")
    brg_path  = discover_input(BRIDGES_PATH, "bridges.shp")

    # Ler dados base
    par_perc  = gpd.read_file(shp_dir / "paragens_percursos.shp")
    shapes_ln = gpd.read_file(shp_dir / "shapes_lines.shp")
    conc      = gpd.read_file(conc_path)
    brg       = gpd.read_file(brg_path)

    # Totais por pattern
    total_stops, total_ext = calcular_totais(par_perc, shapes_ln)

    # Paragens por concelho
    st_int = gpd.sjoin(par_perc.to_crs(conc.crs), conc, how="inner", predicate="within")
    cname = concelho_field_name(st_int.columns.tolist())
    stops_count = st_int.groupby(["pattern_id", cname]).size().reset_index(name="stop_count")

    # Extensão por concelho (descontando pontes)
    lines_no_b = gpd.overlay(shapes_ln.to_crs(brg.crs), brg, how="difference")
    li_int = gpd.overlay(lines_no_b.to_crs(conc.crs), conc, how="intersection")
    proj = li_int.to_crs("EPSG:3857")
    li_int["extension_km"] = proj.geometry.length / 1000.0

    ext = (
        li_int.groupby(["pattern_id", cname])["extension_km"].sum().reset_index()
        .merge(total_ext, on="pattern_id", how="left")
    )

    # Pivot paragens (linhas: pattern_id; colunas: concelho)
    pivot_paragens = stops_count.pivot_table(
        index="pattern_id", columns=cname, values="stop_count", aggfunc="sum", fill_value=0
    )
    pivot_paragens["Grand Total"] = pivot_paragens.sum(axis=1)
    pivot_paragens = pivot_paragens.reset_index()

    ext = ext.rename(columns={cname: "Concelho"})[
        ["pattern_id", "Concelho", "extension_km", "total_extension_km"]
    ]
    return ext, pivot_paragens


# ORQUESTRAÇÃO
def run_pipeline() -> None:
    for area in AREAS:
        area_dir = BASE / area
        if not area_dir.exists():
            log(f"[Aviso] Pasta não encontrada: {area_dir}")
            continue

        log(f"\n=== {area} ===")
        month_dir = latest_month_folder_by_name(area_dir)
        if not month_dir:
            log("  • Sem pastas de mês — ignorado.")
            continue
        log(f"- Último mês detetado: {month_dir.name}")

        force_ref = ("Área 4" in area)  # Área 4 força REF
        gtfs_dir = find_gtfs_candidate(month_dir, force_ref=force_ref)
        if not gtfs_dir:
            log("  • Nenhuma pasta/ZIP GTFS com YEAR/REF — ignorado.")
            continue
        log(f"  • GTFS escolhido: {gtfs_dir.name}")

        shp_dir = gtfs_dir / "shapefiles"
        shp_dir.mkdir(exist_ok=True)

        # GTFS -> SHPs
        try:
            build_shapefiles_from_gtfs_complete(gtfs_dir, shp_dir)
            log("    ✓ Shapefiles completos gerados (stops, stop_times, shapes_points, shapes_lines, paragens_percursos).")
        except Exception as e:
            log(f"    [ERRO GTFS->SHP] {e}")
            continue

        # Repartição
        try:
            ext_df, pivot_par_df = correr_reparticao(shp_dir)

            area_num = re.search(r"Área\s*(\d+)", area).group(1)
            out_name = f"{TODAY_TAG}_A{area_num}_reparticao km_por municipio.xlsx"
            out_path = OUT_DIR / out_name

            with pd.ExcelWriter(out_path, engine="xlsxwriter") as xlw:
                ext_df.to_excel(xlw, index=False, sheet_name="extension_per_municipality")
                pivot_par_df.to_excel(xlw, index=False, sheet_name="paragens_pro municipio")

                # ajustar larguras
                for ws_name, df in {"extension_per_municipality": ext_df,
                                    "paragens_pro municipio": pivot_par_df}.items():
                    ws = xlw.sheets[ws_name]
                    for col_idx, col in enumerate(df.columns):
                        try:
                            width = max(12, min(40, int(df[col].astype(str).str.len().max()) + 2))
                        except Exception:
                            width = 14
                        ws.set_column(col_idx, col_idx, width)

            log(f"    ✓ Ficheiro final guardado: {out_path}")

        except FileNotFoundError as e:
            log(f"    [ERRO INPUT FIXO] {e} — coloca os ficheiros em C:\\VSC\\Km_p_municipio\\inputs\\ ou ajusta os caminhos no topo.")
            continue
        except Exception as e:
            log(f"    [ERRO REPARTIÇÃO] {e}")
            continue


if __name__ == "__main__":
    run_pipeline()