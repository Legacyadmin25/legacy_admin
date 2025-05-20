from barcode import Code128
from barcode.writer import ImageWriter

def render_barcode(easypay_no: str, output_path: str):
    """
    Generates a Code128C PNG at ≥200 DPI.
    """
    writer = ImageWriter()
    writer.set_options({'dpi': 300, 'module_height': 15})  # tweak mm→px
    Code128(easypay_no, writer=writer, add_checksum=False).write(open(output_path, 'wb'))
