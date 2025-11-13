from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FileField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileAllowed

class OportunidadForm(FlaskForm):
    """
    Formulario de Oportunidad.
    Define los campos y validaciones, y permite cargar dinámicamente
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

    id_tipo_innovacion = SelectField('Tipo de Innovación', coerce=int, validators=[
        DataRequired(message='Debe seleccionar un tipo de innovación')
    ])

    id_foco_innovacion = SelectField('Foco de Innovación', coerce=int, validators=[
        DataRequired(message='Debe seleccionar un foco de innovación')
    ])

    archivo_multimedia = FileField('Archivo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Solo imágenes o documentos.')
    ])

    creador_por = StringField('Creado Por', validators=[
        Length(max=50, message='El nombre del creador no debe exceder los 50 caracteres')
    ])

    estado = BooleanField('Estado')

    submit = SubmitField('Guardar')

    # 🔹 Carga dinámica y selección automática (para editar)
    def load_dynamic_choices(self, focos, tipos, selected_foco=None, selected_tipo=None):
        """
        Carga las opciones dinámicamente para los campos de selección.
        Maneja tanto tuplas como diccionarios.
        """
        # Manejar si vienen como tuplas o como diccionarios
        if focos and isinstance(focos[0], tuple):
            # Ya vienen como tuplas (id, nombre)
            self.id_foco_innovacion.choices = focos
        else:
            # Vienen como diccionarios
            self.id_foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos]
        
        if tipos and isinstance(tipos[0], tuple):
            # Ya vienen como tuplas (id, nombre)
            self.id_tipo_innovacion.choices = tipos
        else:
            # Vienen como diccionarios
            self.id_tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in tipos]

        # Asignar valores seleccionados
        if selected_foco:
            self.id_foco_innovacion.data = selected_foco
        if selected_tipo:
            self.id_tipo_innovacion.data = selected_tipo

        # Debug
        print("✔ Focos cargados:", self.id_foco_innovacion.choices)
        print("✔ Tipos cargados:", self.id_tipo_innovacion.choices)
        print(f"✔ Foco seleccionado: {self.id_foco_innovacion.data}")
        print(f"✔ Tipo seleccionado: {self.id_tipo_innovacion.data}")