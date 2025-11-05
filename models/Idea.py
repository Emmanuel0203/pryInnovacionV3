# models/Idea.py
from extensions import db

# ======================
# 💡 MODELO IDEA
# ======================
class Idea(db.Model):
    __tablename__ = 'idea'
    __table_args__ = {'schema': 'public'}

    codigo_idea = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    palabras_claves = db.Column(db.String(255))
    recursos_requeridos = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=db.func.now())
    fecha_modificacion = db.Column(db.DateTime)
    estado = db.Column(db.Boolean, default=False)

    # Relaciones foráneas
    id_tipo_innovacion = db.Column(
        db.Integer, 
        db.ForeignKey('public.tipo_innovacion.id_tipo_innovacion')
    )
    id_foco_innovacion = db.Column(
        db.Integer, 
        db.ForeignKey('public.foco_innovacion.id_foco_innovacion')
    )
    id_area = db.Column(db.Integer, db.ForeignKey('public.area_idea.id_area'))
    id_estado = db.Column(db.Integer, db.ForeignKey('public.estado_idea.id_estado'))

    # Relaciones SQLAlchemy
    tipo_innovacion = db.relationship('TipoInnovacion', back_populates='ideas', lazy='joined')
    foco_innovacion = db.relationship('FocoInnovacion', back_populates='ideas', lazy='joined')

    # Muchos a muchos con Usuario (autores)
    autores = db.relationship(
        'Usuario',
        secondary='public.idea_usuario',
        back_populates='ideas_autor',
        lazy='joined'
    )

    def __repr__(self):
        return f'<Idea {self.titulo}>'


# ======================
# ⚙️ TABLA INTERMEDIA IDEA_USUARIO
# ======================
class IdeaUsuario(db.Model):
    __tablename__ = 'idea_usuario'
    __table_args__ = {'schema': 'public'}

    codigo_idea = db.Column(
        db.Integer, 
        db.ForeignKey('public.idea.codigo_idea'),
        primary_key=True
    )
    usuario_email = db.Column(
        db.String(100), 
        db.ForeignKey('public.usuario.email'),
        primary_key=True
    )
