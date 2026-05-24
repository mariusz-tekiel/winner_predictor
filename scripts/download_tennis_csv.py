"""
Downloads Jeff Sackmann tennis CSV files from GitHub.

Repos:
  ATP + Challenger: https://github.com/JeffSackmann/tennis_atp
  WTA:              https://github.com/JeffSackmann/tennis_wta

Usage:
  python scripts/download_tennis_csv.py
  python scripts/download_tennis_csv.py --tours atp wta --years 2019 2020 2021 2022 2023 2024
  python scripts/download_tennis_csv.py --tours challenger --years 2022 2023 2024
"""
import argparse
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Brak httpx. Zainstaluj: pip install httpx")
    sys.exit(1)

BASE_ATP = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"
BASE_WTA = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master"

OUTPUT_DIR = Path(__file__).parent.parent / "backend" / "data" / "tennis_csv"

FILE_TEMPLATES = {
    "atp": (BASE_ATP, "atp_matches_{year}.csv", "atp_{year}.csv"),
    "wta": (BASE_WTA, "wta_matches_{year}.csv", "wta_{year}.csv"),
    "challenger": (BASE_ATP, "atp_challenger_tour_matches_{year}.csv", "atp_challenger_{year}.csv"),
}


def download_file(url: str, dest: Path) -> bool:
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return True
    except Exception as e:
        print(f"  BŁĄD: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Pobiera pliki CSV Sackmann")
    parser.add_argument(
        "--tours", nargs="+", default=["atp", "wta", "challenger"],
        choices=["atp", "wta", "challenger"],
        help="Które tury pobierać (domyślnie: wszystkie)"
    )
    parser.add_argument(
        "--years", nargs="+", type=int,
        default=list(range(2015, 2026)),
        help="Lista lat (domyślnie: 2015–2025)"
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Katalog docelowy: {OUTPUT_DIR}")
    print(f"Tury: {args.tours}")
    print(f"Lata: {args.years[0]}–{args.years[-1]}\n")

    total_ok = total_skip = total_fail = 0

    for tour in args.tours:
        base_url, src_template, dest_template = FILE_TEMPLATES[tour]
        print(f"=== {tour.upper()} ===")

        for year in args.years:
            src_name = src_template.format(year=year)
            dest_name = dest_template.format(year=year)
            dest_path = OUTPUT_DIR / dest_name

            if dest_path.exists():
                size_kb = dest_path.stat().st_size // 1024
                print(f"  {dest_name} — już istnieje ({size_kb} KB), pomijam")
                total_skip += 1
                continue

            url = f"{base_url}/{src_name}"
            print(f"  {dest_name} … ", end="", flush=True)
            ok = download_file(url, dest_path)
            if ok:
                size_kb = dest_path.stat().st_size // 1024
                print(f"OK ({size_kb} KB)")
                total_ok += 1
            else:
                print("brak (rok może nie istnieć)")
                total_fail += 1

            time.sleep(0.3)  # gentle rate limit

        print()

    print(f"Gotowe: {total_ok} pobrano, {total_skip} pominiętych, {total_fail} nieznalezionych")
    print("\nNastępny krok: uruchom trening w aplikacji lub przez API:")
    print("  POST /api/tennis/model/train?tour=atp&years=2019,2020,2021,2022,2023,2024")


if __name__ == "__main__":
    main()
