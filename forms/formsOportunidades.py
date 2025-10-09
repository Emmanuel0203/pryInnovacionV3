from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, FileField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length

class OportunidadForm(FlaskForm):
    titulo = StringField('Título', validators=[
        DataRequired(message='El título es requerido'),
        Length(min=5, max=100, message='El título debe tener entre 5 y 100 caracteres')
    ])
    
    descripcion = TextAreaField('Descripción', validators=[
        DataRequired(message='La descripción es requerida'),
        Length(min=10, max=1000, message='La descripción debe tener entre 10 y 1000 caracteres')
    ])
    
    palabras_claves = StringField('Palabras Clave', validators=[
        DataRequired(message='Las palabras clave son requeridas'),
        Length(min=3, max=200, message='Las palabras clave deben tener entre 3 y 200 caracteres')
    ])
    
    recursos_requeridos = IntegerField('Recursos Requeridos', validators=[
        DataRequired(message='Los recursos requeridos son necesarios')
    ])
    
    archivo_multimedia = FileField('Archivo Multimedia', validators=[
        DataRequired(message='El archivo multimedia es requerido')
    ])
    
    id_tipo_innovacion = SelectField('Tipo de Innovación', coerce=int, validators=[
        DataRequired(message='El tipo de innovación es requerido')
    ])
    
    id_foco_innovacion = SelectField('Foco de Innovación', coerce=int, validators=[
        DataRequired(message='El foco de innovación es requerido')
    ])
    
    creador_por = StringField('Creado Por', validators=[
        Length(max=50, message='El nombre del creador no debe exceder los 50 caracteres')
    ])
    
    estado = BooleanField('Estado')
    
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
        self.id_foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos]
        self.id_tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in tipos]

        # Log the choices for debugging
        print(f"Foco Innovacion Choices: {self.id_foco_innovacion.choices}")
        print(f"Tipo Innovacion Choices: {self.id_tipo_innovacion.choices}")