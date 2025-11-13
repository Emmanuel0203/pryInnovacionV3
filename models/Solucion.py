# models/Solucion.py
from extensions import db

class Solucion(db.Model):
    __tablename__ = 'solucion'
    __table_args__ = {'schema': 'public'}

    codigo_solucion = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    palabras_claves = db.Column(db.String(255))
    recursos_requeridos = db.Column(db.Text)
    archivo_multimedia = db.Column(db.String(255))
    fecha_creacion = db.Column(db.DateTime, default=db.func.now())
    fecha_modificacion = db.Column(db.DateTime)
    
    # ⚙️ Estado como texto o booleano (según tu BD)
    estado = db.Column(db.String(50), default='Pendiente')  # o Boolean si en BD es TRUE/FALSE

    # Relaciones foráneas
    id_tipo_innovacion = db.Column(
        db.Integer,
        db.ForeignKey('public.tipo_innovacion.id_tipo_innovacion')
    )
    id_foco_innovacion = db.Column(
        db.Integer,
        db.ForeignKey('public.foco_innovacion.id_foco_innovacion')
    )
    area_unidad_desarrollo = db.Column(
        db.Integer,
        db.ForeignKey('public.area_idea.id_area')
    )

    # Campos de usuario
    creador_por = db.Column(db.String(100), db.ForeignKey('public.usuario.email'))
    desarrollador_por = db.Column(db.String(100), db.ForeignKey('public.usuario.email'))

    # Relaciones SQLAlchemy
    tipo_innovacion = db.relationship('TipoInnovacion', lazy='joined')
    foco_innovacion = db.relationship('FocoInnovacion', lazy='joined')

    def __repr__(self):
        return f"<Solucion {self.titulo}>"
