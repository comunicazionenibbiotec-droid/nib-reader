import json
import os


BASE_DIRECTORY = os.path.dirname(
    os.path.abspath(__file__)
)


CALIBRATION_FILE = os.path.join(
    BASE_DIRECTORY,
    "lot_calibrations.json"
)


class CalibrationError(Exception):
    pass


def load_calibration_database():
    if not os.path.exists(
        CALIBRATION_FILE
    ):
        raise CalibrationError(
            "lot_calibrations_file_not_found"
        )

    with open(
        CALIBRATION_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        database = json.load(
            file
        )

    if "lots" not in database:
        raise CalibrationError(
            "invalid_calibration_database"
        )

    return database


def get_default_lot_id():
    database = (
        load_calibration_database()
    )

    lot_id = database.get(
        "default_lot_id"
    )

    if not lot_id:
        raise CalibrationError(
            "default_lot_not_defined"
        )

    return lot_id


def get_lot_configuration(
    lot_id=None
):
    database = (
        load_calibration_database()
    )

    if not lot_id:
        lot_id = database.get(
            "default_lot_id"
        )

    lots = database.get(
        "lots",
        {}
    )

    if lot_id not in lots:
        raise CalibrationError(
            "unknown_lot_id"
        )

    configuration = lots[
        lot_id
    ].copy()

    configuration["lot_id"] = (
        lot_id
    )

    configuration[
        "schema_version"
    ] = database.get(
        "schema_version",
        "unknown"
    )

    return configuration


def get_psa_configuration(
    lot_id=None
):
    lot_configuration = (
        get_lot_configuration(
            lot_id
        )
    )

    psa_configuration = (
        lot_configuration.get(
            "psa",
            {}
        )
    )

    if not psa_configuration.get(
        "enabled",
        False
    ):
        raise CalibrationError(
            "psa_reading_disabled_for_lot"
        )

    return psa_configuration


def get_zinc_configuration(
    lot_id=None
):
    lot_configuration = (
        get_lot_configuration(
            lot_id
        )
    )

    zinc_configuration = (
        lot_configuration.get(
            "zinc",
            {}
        )
    )

    if not zinc_configuration.get(
        "enabled",
        False
    ):
        raise CalibrationError(
            "zinc_reading_disabled_for_lot"
        )

    return zinc_configuration


def calibration_available(
    lot_id,
    analyte
):
    lot_configuration = (
        get_lot_configuration(
            lot_id
        )
    )

    analyte_configuration = (
        lot_configuration.get(
            analyte,
            {}
        )
    )

    calibration = (
        analyte_configuration.get(
            "calibration",
            {}
        )
    )

    return bool(
        calibration.get(
            "available",
            False
        )
    )