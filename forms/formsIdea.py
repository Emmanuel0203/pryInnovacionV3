from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, SubmitField,
    HiddenField, BooleanField, IntegerField, DateField
)
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class IdeaForm(FlaskForm):

    codigo_idea = HiddenField('Código de Idea')  
    
    titulo = StringField('Título', validators=[
        DataRequired(message='El título es requerido'),
        Length(min=5, max=100, message='El título debe tener entre 5 y 100 caracteres')
    ])
    
    descripcion = TextAreaField('Descripción', validators=[
        DataRequired(message='La descripción es requerida'),
        Length(min=10, max=1000, message='La descripción debe tener entre 10 y 1000 caracteres')
    ])
    
    palabras_claves = StringField('Palabras Claves', validators=[
        DataRequired(message='Las palabras claves son requeridas'),
        Length(max=200, message='Las palabras claves no pueden exceder los 200 caracteres')
    ])
    
    recursos_requeridos = IntegerField('Recursos Requeridos', validators=[
        Optional(),
        NumberRange(min=0, message='Los recursos requeridos deben ser un número positivo')
    ])
    
    id_tipo_innovacion = SelectField('Tipo de Innovación', coerce=int, validators=[
        DataRequired(message='El tipo de innovación es requerido')
    ])
    
    id_foco_innovacion = SelectField('Foco de Innovación', coerce=int, validators=[
        DataRequired(message='El foco de innovación es requerido')
    ])

    archivo_multimedia = FileField('Archivo Multimedia', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'pdf', 'mp4', 'zip', 'docx'], 'Formato no permitido.')
    ])
    
    fecha_creacion = DateField('Fecha de creación', format='%Y-%m-%d', validators=[Optional()])
    creador_por = StringField('Creador por', validators=[Optional()])
    estado = BooleanField('Estado activo', default=True)

    
    submit = SubmitField('Guardar Idea')
