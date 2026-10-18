import base64
from io import BytesIO
from PIL import Image

def decode_image(data):

    header, encoded = data.split(',')

    return Image.open(
        BytesIO(
            base64.b64decode(
                encoded
            )
        )
    )