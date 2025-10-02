from extensions import db

class Solucion(db.Model):
    __tablename__ = 'solucion'
    __table_args__ = {'schema': 'public'}
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text) 


# models/solucion.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Solucion:
    codigo: int
    titulo: str
    descripcion: str
    fecha_creacion: str
    id_tipo_innovacion: int
    id_foco_innovacion: int
    creador_por: str
    archivo_multimedia: Optional[str] = None
    tipo_innovacion_nombre: Optional[str] = None
    foco_innovacion_nombre: Optional[str] = None