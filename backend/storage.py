from pathlib import Path
import cv2
import json


def create_sample_folder(
    lot_number,
    sample_id
):

    folder = Path(
        f"storage/{lot_number}/{sample_id}"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    return folder


def save_image(
    image,
    filepath
):

    cv2.imwrite(
        str(filepath),
        image
    )


def save_json(
    data,
    filepath
):

    with open(
        filepath,
        "w"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )
