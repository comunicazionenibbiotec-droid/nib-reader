from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qms_models import QmsLot, QmsLotRecordType, QmsProduct
from qms_schemas import LotCreate


QMS_MASTER = [
    ("PM-000104", "Colorimetric pad", "component", "finished_colorimetric_pad", "LR-000104", "colorimetric_pad_manufacturing", "Colorimetric pad manufacturing"),
    ("PM-000098", "Card assembling", "semi_finished", "assembled_uncut_card", "LR-000178", "card_assembling", "Card assembling - card assemblata non tagliata"),
    ("PM-000100", "LF strip", "component", "cut_lateral_flow_strip", "LR-000122", "strip_cutting", "LF card cutting into strips"),
    ("PM-000110-001", "ZenPSA Pro", "finished_device", "finished_device", "LR-000198", "finished_device_assembly", "ZenPSA Pro finished device assembly"),
]


def seed_qms_master_data(session: Session):
    for pm, name, category, stage, lr, operation_code, operation_name in QMS_MASTER:
        product = session.scalar(select(QmsProduct).where(QmsProduct.pm_code == pm))
        if product is None:
            product = QmsProduct(
                pm_code=pm,
                product_name=name,
                product_category=category,
                product_stage=stage,
                active=True,
            )
            session.add(product)
            session.flush()

        record_type = session.scalar(
            select(QmsLotRecordType).where(
                QmsLotRecordType.lr_document_code == lr
            )
        )
        if record_type is None:
            session.add(
                QmsLotRecordType(
                    product_id=product.id,
                    lr_document_code=lr,
                    operation_code=operation_code,
                    operation_name=operation_name,
                    stage=stage,
                    progressive_digits=3,
                    active=True,
                )
            )
    session.commit()


def next_progressive(session: Session, record_type_id):
    value = session.scalar(
        select(func.max(QmsLot.lot_progressive)).where(
            QmsLot.lot_record_type_id == record_type_id
        )
    )
    return 0 if value is None else int(value) + 1


def build_full_code(record_type: QmsLotRecordType, progressive: int):
    return (
        f"{record_type.lr_document_code}-"
        f"{progressive:0{record_type.progressive_digits}d}"
    )


def create_lot(session: Session, payload: LotCreate):
    record_type = session.get(
        QmsLotRecordType,
        payload.lot_record_type_id,
    )
    if record_type is None or not record_type.active:
        raise ValueError("Tipologia LR non disponibile")

    progressive = next_progressive(session, record_type.id)
    lot = QmsLot(
        lot_record_type_id=record_type.id,
        pm_code=record_type.product.pm_code,
        lr_document_code=record_type.lr_document_code,
        lot_progressive=progressive,
        full_lot_record_code=build_full_code(record_type, progressive),
        manufacturing_date=payload.manufacturing_date,
        status="draft",
    )
    session.add(lot)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError(
            "Conflitto nella numerazione del lotto. Riprovare."
        )

    session.refresh(lot)
    return lot
