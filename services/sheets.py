import logging
from datetime import datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

from config import settings
from models.signal import SignalRecord, SignalResponse

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Headers exactos según ARCHITECTURE.md
HEADERS = [
    "rank", "signal_id", "timestamp_utc", "analysis_window_hours", "pair", "asset_name",
    "direction", "entry_price", "expected_min_pct", "expected_max_pct",
    "target_price_min", "target_price_max", "confidence_score", "bullish_score",
    "bearish_score", "expected_edge", "primary_catalyst", "narrative",
    "status", "exit_price", "actual_move_pct", "accuracy",
    "check_timestamp_utc", "notes",
]


class SheetsClient:
    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.sheet: Optional[gspread.Worksheet] = None
        self._connect()

    def _connect(self):
        try:
            creds_dict = settings.get_service_account_credentials()
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            self.client = gspread.authorize(creds)
            spreadsheet = self.client.open_by_key(settings.GOOGLE_SHEETS_ID)
            # Usar la primera hoja
            self.sheet = spreadsheet.sheet1
            logger.info("Google Sheets connected: %s", spreadsheet.title)
        except Exception as e:
            logger.error("Failed to connect to Google Sheets: %s", e)
            raise

    def _ensure_headers(self):
        """Escribe headers si la hoja está vacía."""
        try:
            first_row = self.sheet.row_values(1)
            if not first_row:
                self.sheet.append_row(HEADERS)
                logger.info("Headers written to sheet")
        except Exception as e:
            logger.error("Error ensuring headers: %s", e)

    def append_signal(self, record: SignalRecord) -> None:
        self._ensure_headers()
        row = [
            record.rank,
            record.signal_id,
            record.timestamp_utc,
            record.analysis_window_hours,
            record.pair,
            record.asset_name,
            record.direction,
            record.entry_price,
            record.expected_min_pct,
            record.expected_max_pct,
            record.target_price_min,
            record.target_price_max,
            record.confidence_score,
            record.bullish_score,
            record.bearish_score,
            record.expected_edge,
            record.primary_catalyst,
            record.narrative,
            record.status,
            record.exit_price,
            record.actual_move_pct,
            record.accuracy,
            record.check_timestamp_utc,
            record.notes,
        ]
        # Convertir None a string vacía para evitar errores de gspread
        row = ["" if v is None else v for v in row]
        try:
            self.sheet.append_row(row)
            logger.info("Signal appended: %s", record.signal_id)
        except Exception as e:
            logger.error("Error appending signal: %s", e)
            raise

    def update_signal_check(self, signal_id: str, status: str, exit_price: float,
                            actual_move_pct: float, accuracy: str) -> None:
        """Actualiza una fila existente con los resultados de verificación."""
        try:
            # Buscar la fila por signal_id (columna B, índice 2)
            cell = self.sheet.find(signal_id, in_column=2)
            if not cell:
                logger.warning("Signal %s not found for update", signal_id)
                return
            row_idx = cell.row
            # Columnas: T=status(20), U=exit_price(21), V=actual_move_pct(22), W=accuracy(23), X=check_timestamp(24)
            updates = [
                (row_idx, 20, status),
                (row_idx, 21, exit_price),
                (row_idx, 22, actual_move_pct),
                (row_idx, 23, accuracy),
                (row_idx, 24, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
            ]
            for r, c, val in updates:
                self.sheet.update_cell(r, c, val)
            logger.info("Signal updated: %s -> %s", signal_id, status)
        except Exception as e:
            logger.error("Error updating signal %s: %s", signal_id, e)
            raise

    def _clean_record(self, rec: dict) -> dict:
        """Convierte strings vacíos a None solo en campos numéricos."""
        cleaned = dict(rec)
        numeric_fields = {
            "entry_price", "expected_min_pct", "expected_max_pct",
            "target_price_min", "target_price_max", "confidence_score",
            "bullish_score", "bearish_score", "expected_edge",
            "exit_price", "actual_move_pct", "rank",
        }
        for key in numeric_fields:
            if key in cleaned and cleaned[key] == "":
                cleaned[key] = None
        return cleaned

    def get_pending_signals(self) -> list[SignalRecord]:
        """Devuelve todas las señales con status PENDING."""
        try:
            self._ensure_headers()
            records = self.sheet.get_all_records()
            pending = []
            for rec in records:
                if rec.get("status") == "PENDING":
                    try:
                        pending.append(SignalRecord(**self._clean_record(rec)))
                    except Exception as e:
                        logger.warning("Invalid pending record skipped: %s", e)
            return pending
        except Exception as e:
            logger.error("Error reading pending signals: %s", e)
            return []

    def get_recent_signals(self, limit: int = 20) -> list[SignalRecord]:
        """Devuelve las N señales más recientes (últimas filas)."""
        try:
            self._ensure_headers()
            records = self.sheet.get_all_records()
            # Ordenar por signal_id descendente (asume que signal_id incluye timestamp)
            records.sort(key=lambda r: str(r.get("signal_id", "")), reverse=True)
            result = []
            for rec in records[:limit]:
                try:
                    result.append(SignalRecord(**self._clean_record(rec)))
                except Exception:
                    continue
            return result
        except Exception as e:
            logger.error("Error reading recent signals: %s", e)
            return []

    def get_last_signal_timestamp(self) -> Optional[datetime]:
        """Devuelve el timestamp de la señal más reciente, o None si no hay."""
        try:
            self._ensure_headers()
            records = self.sheet.get_all_records()
            if not records:
                return None
            # Ordenar por timestamp descendente
            records.sort(key=lambda r: str(r.get("timestamp_utc", "")), reverse=True)
            last_ts_str = records[0].get("timestamp_utc")
            if last_ts_str:
                return datetime.fromisoformat(last_ts_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.warning("Error reading last signal timestamp: %s", e)
        return None
