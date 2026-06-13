from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


HISTORICAL_FILE = "Desi_talep.xlsx"
FORECAST_FILE = "Tahminlenen_Talep.xlsx"
DEFAULT_HORIZON_DAYS = 31


def _resolve_input_path(base_dir: Path, path_text: str) -> Path:
	path = Path(path_text)
	if path.is_absolute():
		return path

	local_path = base_dir / path
	if local_path.exists():
		return local_path

	common_path = base_dir / "ortak" / "data" / path
	if common_path.exists():
		return common_path

	return local_path


def _resolve_output_path(base_dir: Path, path_text: str) -> Path:
	path = Path(path_text)
	if path.is_absolute():
		return path

	common_dir = base_dir / "ortak" / "data"
	if common_dir.exists():
		return common_dir / path

	return base_dir / path


def _normalize_history_frame(raw_df: pd.DataFrame) -> pd.DataFrame:
	if raw_df.shape[1] < 4:
		raise ValueError("Desi_talep.xlsx dosyasında beklenen en az 4 sütun bulunamadı.")

	history_df = raw_df.iloc[:, :4].copy()
	history_df.columns = ["Cikis", "Varis", "Tarih", "Talep"]
	history_df["Cikis"] = history_df["Cikis"].astype(str).str.strip()
	history_df["Varis"] = history_df["Varis"].astype(str).str.strip()
	history_df["Tarih"] = pd.to_datetime(history_df["Tarih"]).dt.normalize()
	history_df["Talep"] = pd.to_numeric(history_df["Talep"], errors="coerce").fillna(0.0)
	return history_df


def _build_route_series(history_df: pd.DataFrame) -> dict[tuple[str, str], pd.Series]:
	full_dates = pd.date_range(history_df["Tarih"].min(), history_df["Tarih"].max(), freq="D")
	route_series: dict[tuple[str, str], pd.Series] = {}

	for (origin, destination), route_df in history_df.groupby(["Cikis", "Varis"]):
		daily = (
			route_df.groupby("Tarih", as_index=True)["Talep"].sum().astype(float)
			.reindex(full_dates, fill_value=0.0)
		)
		route_series[(origin, destination)] = daily

	return route_series


def _forecast_route_series(route_daily: pd.Series, future_dates: pd.DatetimeIndex) -> list[float]:
	overall_mean = float(route_daily.mean()) if len(route_daily) else 0.0
	recent_window = min(28, len(route_daily))
	recent_mean = float(route_daily.tail(recent_window).mean()) if recent_window else overall_mean

	weekday_means = route_daily.groupby(route_daily.index.dayofweek).mean().to_dict()
	forecasts: list[float] = []

	for future_date in future_dates:
		weekday_mean = float(weekday_means.get(future_date.dayofweek, overall_mean))
		if overall_mean > 0:
			weekday_factor = weekday_mean / overall_mean
			weekday_factor = min(1.4, max(0.6, 0.6 + 0.4 * weekday_factor))
		else:
			weekday_factor = 1.0

		base_level = 0.7 * recent_mean + 0.3 * overall_mean
		forecast_value = max(0.0, base_level * weekday_factor)
		forecasts.append(round(forecast_value, 2))

	return forecasts


def generate_demand_forecast(
	historical_path: Path | str | None = None,
	output_path: Path | str | None = None,
	horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> pd.DataFrame:
	base_dir = Path(__file__).resolve().parent
	historical_file = _resolve_input_path(base_dir, historical_path or HISTORICAL_FILE)
	output_file = _resolve_output_path(base_dir, output_path or FORECAST_FILE)

	history_df = _normalize_history_frame(pd.read_excel(historical_file))
	route_series_map = _build_route_series(history_df)

	last_date = history_df["Tarih"].max()
	future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")

	forecast_rows: list[dict[str, object]] = []
	for (origin, destination), route_daily in sorted(route_series_map.items()):
		forecast_values = _forecast_route_series(route_daily, future_dates)
		for future_date, forecast_value in zip(future_dates, forecast_values):
			forecast_rows.append(
				{
					"Çıkış Transfer Merkezi": origin,
					"Varış Transfer Merkezi": destination,
					"Tarih": future_date,
					"Tahmini Desi": forecast_value,
				}
			)

	forecast_df = pd.DataFrame(
		forecast_rows,
		columns=["Çıkış Transfer Merkezi", "Varış Transfer Merkezi", "Tarih", "Tahmini Desi"],
	).sort_values(["Tarih", "Çıkış Transfer Merkezi", "Varış Transfer Merkezi"]).reset_index(drop=True)

	with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
		forecast_df.to_excel(writer, index=False, sheet_name="Sheet1")

	return forecast_df


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Desi_talep.xlsx verisinden Tahminlenen_Talep.xlsx oluşturur."
	)
	parser.add_argument(
		"--input",
		default=HISTORICAL_FILE,
		help="Geçmiş talep dosyası (varsayılan: Desi_talep.xlsx)",
	)
	parser.add_argument(
		"--output",
		default=FORECAST_FILE,
		help="Yazılacak tahmin dosyası (varsayılan: Tahminlenen_Talep.xlsx)",
	)
	parser.add_argument(
		"--horizon",
		type=int,
		default=DEFAULT_HORIZON_DAYS,
		help="Kaç gün ileri tahmin üretileceği (varsayılan: 31)",
	)
	args = parser.parse_args()

	forecast_df = generate_demand_forecast(args.input, args.output, args.horizon)
	output_file = _resolve_output_path(Path(__file__).resolve().parent, args.output)
	print(f"[OK] Tahmin dosyasi olusturuldu: {output_file}")
	print(f"[OK] Kayit sayisi: {len(forecast_df)}")


if __name__ == "__main__":
	main()
