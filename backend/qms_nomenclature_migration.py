from sqlalchemy import text

from database import engine


def run_qms_nomenclature_migration() -> None:
    statements = [
        """
        UPDATE qms_products
        SET product_name = 'Colorimetric pad'
        WHERE pm_code = 'PM-000104'
        """,
        """
        UPDATE qms_lot_record_types
        SET operation_name = 'Colorimetric pad'
        WHERE lr_document_code = 'LR-000104'
        """,
        """
        UPDATE qms_products
        SET product_name = 'LF strips'
        WHERE pm_code = 'PM-000100'
        """,
        """
        UPDATE qms_lot_record_types
        SET operation_name = 'LF strips'
        WHERE lr_document_code = 'LR-000122'
        """,
        """
        UPDATE qms_products
        SET product_name = 'ZenPSA Pro device'
        WHERE pm_code = 'PM-000110-001'
        """,
        """
        UPDATE qms_lot_record_types
        SET operation_name = 'ZenPSA Pro device'
        WHERE lr_document_code = 'LR-000198'
        """,
        """
        UPDATE qms_products
        SET active = FALSE
        WHERE pm_code = 'PM-000098'
        """,
        """
        UPDATE qms_lot_record_types
        SET active = FALSE
        WHERE lr_document_code = 'LR-000178'
        """,
    ]

    verification_query = """
        SELECT
            p.pm_code,
            p.product_name,
            p.active,
            t.lr_document_code,
            t.operation_name,
            t.active AS lot_record_type_active
        FROM qms_products p
        LEFT JOIN qms_lot_record_types t
            ON t.product_id = p.id
        WHERE p.pm_code IN (
            'PM-000104',
            'PM-000100',
            'PM-000110-001',
            'PM-000098'
        )
        ORDER BY p.pm_code
    """

    with engine.begin() as connection:
        database_name = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

        if database_name != "dbmg3cwffes36w":
            raise RuntimeError(
                f"Migrazione QMS interrotta: database inatteso {database_name}"
            )

        for statement in statements:
            connection.execute(text(statement))

        rows = connection.execute(
            text(verification_query)
        ).mappings().all()

    print("QMS_NOMENCLATURE_MIGRATION_COMPLETED")

    for row in rows:
        print(
            "QMS_RESULT",
            row["pm_code"],
            row["product_name"],
            row["active"],
            row["lr_document_code"],
            row["operation_name"],
            row["lot_record_type_active"],
        )