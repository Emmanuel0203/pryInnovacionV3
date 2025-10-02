import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "app/static/uploads"

def save_file(file):
    """Guarda un archivo subido en el servidor y retorna la ruta relativa."""
    if not file:
        return None
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    return f"/static/uploads/{filename}"
