# models/__init__.py
# Importar modelos
from .Usuario import Usuario
from .Idea import Idea
from .Oportunidad import Oportunidad
from .Solucion import Solucion
from .TipoInnovacion import TipoInnovacion
from .FocoInnovacion import FocoInnovacion
from .Perfil import Perfil

# Exportar modelos
__all__ = [
    'Usuario',
    'Idea',
    'Oportunidad',
    'Solucion',
    'TipoInnovacion',
    'FocoInnovacion',
    'Perfil'
]

