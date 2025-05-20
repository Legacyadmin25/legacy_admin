import qrcode

def render_qr(data_url: str, output_path: str):
    img = qrcode.make(data_url)
    img.save(output_path)
