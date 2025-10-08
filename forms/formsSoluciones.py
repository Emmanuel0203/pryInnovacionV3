# forms/formsSoluciones/formsSoluciones.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FileField, DateField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileAllowed

class SolucionForm(FlaskForm):
    """
    Formulario de Solución. 
    Se encarga únicamente de definir los campos y validaciones.
    Las opciones de los select son cargadas dinámicamente
    desde la vista usando el servicio.
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
    
    recursos_requeridos = TextAreaField('Recursos Requeridos', validators=[
        DataRequired(message='Los recursos requeridos son necesarios'),
        Length(max=500, message='Los recursos requeridos no deben exceder los 500 caracteres')
    ])
    
    tipo_innovacion = SelectField('Tipo de Innovación', coerce=int, validators=[
        DataRequired(message='Debe seleccionar un tipo de innovación')
    ])
    
    foco_innovacion = SelectField('Foco de Innovación', coerce=int, validators=[
        DataRequired(message='Debe seleccionar un foco de innovación')
    ])

    archivo_multimedia = FileField('Archivo', validators=[
        FileAllowed(['jpg', 'png', 'pdf'], 'Solo imágenes o documentos.')
    ])
    
    fecha_creacion = DateField('Fecha de creación', format='%Y-%m-%d')
    
    submit = SubmitField('Guardar')

    def load_dynamic_choices(self, focos, tipos):
        """
        Load dynamic choices for the form fields.

        Parameters
        ----------
        focos : list
            List of focus options fetched from the API.
        tipos : list
            List of innovation types fetched from the API.
        """
        self.foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos]
        self.tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in tipos]

        # Log the choices for debugging
        print(f"Foco Innovacion Choices: {self.foco_innovacion.choices}")
        print(f"Tipo Innovacion Choices: {self.tipo_innovacion.choices}")
