"""
CSV and Spreadsheet Data Importer with Dry-Run Validation and Atomic Rollback.
"""

import csv
import io
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple


@dataclass
class ImportRowError:
    row_number: int
    field: str
    message: str


@dataclass
class ImportResult:
    total_rows: int
    valid_rows: int
    error_rows: int
    errors: List[ImportRowError] = field(default_factory=list)
    is_dry_run: bool = True
    imported_records: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = False


class CsvDataImporter:
    """
    Imports structured customer, invoice, and contact records from CSV.
    Guarantees atomic rollback on validation failure.
    """

    REQUIRED_CUSTOMER_FIELDS = {"customer_name", "email", "country"}

    @classmethod
    def import_customers_csv(
        cls, csv_text: str, dry_run: bool = True
    ) -> ImportResult:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        if not reader.fieldnames:
            return ImportResult(
                total_rows=0,
                valid_rows=0,
                error_rows=1,
                errors=[ImportRowError(0, "header", "Empty or unparseable CSV header")],
                is_dry_run=dry_run,
                success=False,
            )

        missing_fields = cls.REQUIRED_CUSTOMER_FIELDS - set(reader.fieldnames)
        if missing_fields:
            return ImportResult(
                total_rows=0,
                valid_rows=0,
                error_rows=1,
                errors=[ImportRowError(0, "header", f"Missing required headers: {list(missing_fields)}")],
                is_dry_run=dry_run,
                success=False,
            )

        valid_records = []
        errors = []
        row_idx = 1

        for row in reader:
            row_idx += 1
            row_errors = []

            # Validate customer_name
            name = (row.get("customer_name") or "").strip()
            if not name:
                row_errors.append(ImportRowError(row_idx, "customer_name", "customer_name cannot be empty"))

            # Validate email
            email = (row.get("email") or "").strip()
            if not email or "@" not in email:
                row_errors.append(ImportRowError(row_idx, "email", f"Invalid email format: '{email}'"))

            # Validate country (ISO 2-letter)
            country = (row.get("country") or "").strip()
            if len(country) != 2:
                row_errors.append(ImportRowError(row_idx, "country", f"Country must be 2-letter ISO code: '{country}'"))

            if row_errors:
                errors.extend(row_errors)
            else:
                valid_records.append({
                    "customer_name": name,
                    "email": email,
                    "country": country.upper(),
                })

        total = len(valid_records) + len(errors)
        success = len(errors) == 0

        # Atomic rollback: if any errors occurred, imported_records is empty
        final_imported = valid_records if (success and not dry_run) else []

        return ImportResult(
            total_rows=total,
            valid_rows=len(valid_records),
            error_rows=len(errors),
            errors=errors,
            is_dry_run=dry_run,
            imported_records=final_imported,
            success=success,
        )
