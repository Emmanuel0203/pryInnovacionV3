# forms/formsSoluciones/formsSoluciones.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FileField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileAllowed

class SolucionForm(FlaskForm):
    """
    Formulario de Solución. 
    Define los campos, validaciones y permite cargar dinámicamente
    las opciones de los campos select desde la vista.
    """

    titulo = StringField('Título', validators=[
        DataRequired(message='El título es requerido'),
        Length(min=3, max=100, message='El título debe tener entre 3 y 100 caracteres')
    ])
    
    descripcion = TextAreaField('Descripción', validators=[
        DataRequired(message='La descripción es requerida'),
        Length(min=10, max=1000, message='La descripción debe tener entre 10 y 1000 caracteres')
    ])
    
    palabras_claves = StringField('Palabras Clave', validators=[
        DataRequired(message='Las palabras clave son requeridas'),
        Length(max=200, message='Las palabras clave no deben exceder los 200 caracteres')
    ])
    
    recursos_requeridos = IntegerField('Recursos Requeridos', validators=[
        DataRequired(message='Los recursos requeridos son necesarios')
    ])
    
    tipo_innovacion = SelectField('Tipo de Innovación', coerce=int, validators=[
        DataRequired(message='Debe seleccionar un tipo de innovación')
    ])
    
    foco_innovacion = SelectField('Foco de Innovación', coerce=int, validators=[
        DataRequired(message='Debe seleccionar un foco de innovación')
    ])

    archivo_multimedia = FileField('Archivo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Solo imágenes o documentos PDF.')
    ])
    
    creador_por = StringField('Creado Por', validators=[
        Length(max=50, message='El nombre del creador no debe exceder los 50 caracteres')
    ])

    estado = BooleanField("Estado (Aprobado)", default=False)


    submit = SubmitField('Guardar')

    def load_dynamic_choices(self, focos, tipos, selected_foco=None, selected_tipo=None):
        """
        Carga las opciones dinámicamente para los campos de selección.
        """
        self.foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos]
        self.tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in tipos]

        if selected_foco:
            self.foco_innovacion.data = selected_foco
        if selected_tipo:
            self.tipo_innovacion.data = selected_tipo

        print(f"[DEBUG] Foco Innovacion Choices: {self.foco_innovacion.choices}")
        print(f"[DEBUG] Tipo Innovacion Choices: {self.tipo_innovacion.choices}")
