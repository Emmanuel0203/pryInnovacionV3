// ajax.js - Manejo de operaciones AJAX para ideas

$(document).ready(function() {
    
    // ============================================
    // ELIMINAR IDEA CON CONFIRMACIÓN
    // ============================================
    $('.btn-delete-idea').on('click', function(e) {
        e.preventDefault();
        
        const codigoIdea = $(this).data('id');
        const titulo = $(this).data('titulo') || 'esta idea';
        
        if (confirm(`¿Estás seguro de que deseas eliminar "${titulo}"?`)) {
            // Crear formulario y enviarlo por POST
            const form = $('<form>', {
                'method': 'POST',
                'action': `/ideas/delete/${codigoIdea}`
            });
            
            // Agregar token CSRF si existe
            const csrfToken = $('meta[name="csrf-token"]').attr('content');
            if (csrfToken) {
                form.append($('<input>', {
                    'type': 'hidden',
                    'name': 'csrf_token',
                    'value': csrfToken
                }));
            }
            
            $('body').append(form);
            form.submit();
        }
    });

    
    // ============================================
    // CONFIRMAR IDEA (APROBAR)
    // ============================================
    $('.btn-confirm-idea').on('click', function(e) {
        e.preventDefault();
        
        const codigoIdea = $(this).data('id');
        const titulo = $(this).data('titulo') || 'esta idea';
        
        if (confirm(`¿Deseas aprobar la idea "${titulo}"?`)) {
            $.ajax({
                url: `/ideas/confirmar/${codigoIdea}`,
                method: 'POST',
                data: { confirmar: 'true' },
                success: function(response) {
                    showNotification('Idea aprobada exitosamente', 'success');
                    setTimeout(() => location.reload(), 1500);
                },
                error: function(xhr) {
                    showNotification('Error al aprobar la idea', 'danger');
                    console.error('Error:', xhr);
                }
            });
        }
    });

    
    // ============================================
    // FILTROS DINÁMICOS EN LISTADO
    // ============================================
    $('#filtro-tipo, #filtro-foco, #filtro-estado').on('change', function() {
        const tipo = $('#filtro-tipo').val();
        const foco = $('#filtro-foco').val();
        const estado = $('#filtro-estado').val();
        
        let url = '/ideas/?';
        const params = [];
        
        if (tipo) params.push(`tipo_innovacion=${tipo}`);
        if (foco) params.push(`foco_innovacion=${foco}`);
        if (estado) params.push(`estado=${estado}`);
        
        url += params.join('&');
        window.location.href = url;
    });

    
    // ============================================
    // LIMPIAR FILTROS
    // ============================================
    $('#btn-limpiar-filtros').on('click', function() {
        window.location.href = '/ideas/';
    });

    
    // ============================================
    // VALIDACIÓN DE FORMULARIO DE CREACIÓN
    // ============================================
    $('#form-create-idea').on('submit', function(e) {
        const titulo = $('#titulo').val().trim();
        const descripcion = $('#descripcion').val().trim();
        
        if (titulo.length < 5) {
            e.preventDefault();
            showNotification('El título debe tener al menos 5 caracteres', 'warning');
            return false;
        }
        
        if (descripcion.length < 20) {
            e.preventDefault();
            showNotification('La descripción debe tener al menos 20 caracteres', 'warning');
            return false;
        }
    });

    
    // ============================================
    // PREVISUALIZACIÓN DE ARCHIVO
    // ============================================
    $('#archivo_multimedia').on('change', function() {
        const file = this.files[0];
        if (file) {
            const fileSize = (file.size / 1024 / 1024).toFixed(2); // MB
            const fileName = file.name;
            
            if (fileSize > 10) {
                showNotification('El archivo no debe superar 10MB', 'warning');
                $(this).val('');
                return;
            }
            
            $('#file-preview').html(`
                <div class="alert alert-info">
                    <i class="fas fa-file"></i> ${fileName} (${fileSize} MB)
                </div>
            `);
        }
    });

    
    // ============================================
    // BÚSQUEDA EN TIEMPO REAL (SI TIENES DATATABLE)
    // ============================================
    if ($.fn.DataTable) {
        $('#tabla-ideas').DataTable({
            language: {
                url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
            },
            pageLength: 10,
            order: [[0, 'desc']], // Ordenar por primera columna descendente
            responsive: true
        });
    }

    
    // ============================================
    // FUNCIÓN AUXILIAR: MOSTRAR NOTIFICACIONES
    // ============================================
    function showNotification(message, type = 'info') {
        // Si usas Bootstrap alerts
        const alertClass = `alert-${type}`;
        const alert = $(`
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);
        
        $('#notification-container').append(alert);
        
        setTimeout(() => {
            alert.fadeOut(300, function() { $(this).remove(); });
        }, 3000);
    }

    
    // ============================================
    // CONTADOR DE CARACTERES
    // ============================================
    $('textarea[maxlength]').each(function() {
        const maxLength = $(this).attr('maxlength');
        const counterId = $(this).attr('id') + '-counter';
        
        $(this).after(`<small id="${counterId}" class="form-text text-muted">
            0 / ${maxLength} caracteres
        </small>`);
        
        $(this).on('input', function() {
            const currentLength = $(this).val().length;
            $(`#${counterId}`).text(`${currentLength} / ${maxLength} caracteres`);
        });
    });

});


// ============================================
// EXPORTAR FUNCIONES GLOBALES (SI ES NECESARIO)
// ============================================
window.deleteIdea = function(codigoIdea, titulo) {
    if (confirm(`¿Eliminar "${titulo}"?`)) {
        window.location.href = `/ideas/delete/${codigoIdea}`;
    }
};

window.confirmIdea = function(codigoIdea) {
    if (confirm('¿Aprobar esta idea?')) {
        $.post(`/ideas/confirmar/${codigoIdea}`, { confirmar: 'true' })
            .done(() => {
                alert('Idea aprobada');
                location.reload();
            })
            .fail(() => alert('Error al aprobar'));
    }
};