/**
 * FUNCIONES GLOBALES
 */
function actualizarBarra() {
    const total = document.querySelectorAll('.btn-group-mobile').length;
    const respondidos = document.querySelectorAll('.item-radio:checked').length;
    
    if (total === 0) return;

    const perc = Math.round((respondidos / total) * 100);
    const bar = document.getElementById('checklist-progress');
    const texto = document.getElementById('progreso-texto');

    if (bar && texto) {
        bar.style.width = perc + '%';
        texto.innerText = perc + '%';
        
        // Colores dinámicos según avance
        if (perc < 40) {
            bar.className = "progress-bar progress-bar-striped progress-bar-animated bg-danger";
        } else if (perc < 99) {
            bar.className = "progress-bar progress-bar-striped progress-bar-animated bg-warning";
        } else {
            bar.className = "progress-bar bg-success"; 
            if (window.navigator.vibrate) window.navigator.vibrate([30, 50, 30]);
        }
    }
}

function actualizarChecklist() {
    const res = [];
    const resultadosInput = document.getElementById('resultados-checklist');
    
    document.querySelectorAll('.item-radio:checked').forEach(r => {
        const id = r.dataset.itemId;
        const obsInput = document.querySelector(`.item-observacion[data-item-id="${id}"]`);
        const obs = obsInput ? obsInput.value : '';
        res.push({ item_id: id, estado: r.value, observacion: obs });
    });
    
    if (resultadosInput) {
        resultadosInput.value = JSON.stringify(res);
    }
}

function marcarCategoriaBuena(catId) {
    const container = document.getElementById(`cat-body-${catId}`);
    if (!container) return;

    const radiosB = container.querySelectorAll('input[value="B"]');
    radiosB.forEach(radio => {
        radio.checked = true;
    });

    // Feedback visual verde
    container.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
    setTimeout(() => container.style.backgroundColor = 'transparent', 600);

    if (window.navigator.vibrate) window.navigator.vibrate(25);

    // Actualizamos datos y barra inmediatamente
    actualizarChecklist();
    actualizarBarra();
}

/**
 * INICIALIZACIÓN
 */document.addEventListener('DOMContentLoaded', function() {
    // 1. REFERENCIAS A ELEMENTOS DEL FORMULARIO
    const tipoSelect = document.getElementById('id_tipo_inspeccion');
    const vehiculoSelect = document.getElementById('id_vehiculo');
    const kmInput = document.getElementById('id_km_registro');
    const resultadosInput = document.getElementById('resultados-checklist');
    const checklistDiv = document.getElementById('categorias-checklist');

    // 2. LISTENERS DE CAMBIOS (Disparan las funciones)
    if (tipoSelect) tipoSelect.addEventListener('change', cargarCategorias);
    if (vehiculoSelect) vehiculoSelect.addEventListener('change', function() {
        cargarDatosAutocompletados();
        if (this.value) mostrarPaso('#step-2');
    });

    if (kmInput) kmInput.addEventListener('input', function() {
        if (this.value.length >= 3) mostrarPaso('#step-3');
    });

    /**
     * FUNCIÓN: MOSTRAR PASOS CON ANIMACIÓN
     */
    function mostrarPaso(selector) {
        const el = document.querySelector(selector);
        if (el && (el.style.display === 'none' || el.style.display === '')) {
            el.style.opacity = 0;
            el.style.display = 'block';
            setTimeout(() => {
                el.style.transition = 'opacity 0.5s ease';
                el.style.opacity = 1;
            }, 10);
        }
    }

    /**
     * FUNCIÓN: CARGAR CATEGORÍAS FILTRADAS
     */
    async function cargarCategorias() {
        const tipo = tipoSelect.value;
        const vehiculo = vehiculoSelect.value;
        
        if (!tipo || !vehiculo) return; 

        try {
            // Llamamos a la API que arreglamos en pgAdmin/Django
            const response = await fetch(`/mantenciones/api/categorias/${tipo}/`);
            const data = await response.json();
            if (data.success) {
                renderizarCategorias(data.categorias);
                mostrarPaso('#step-4');
            }
        } catch (e) { 
            console.error("Error cargando items del checklist", e); 
        }
    }

    /**
     * FUNCIÓN: AUTOCOMPLETAR DATOS DEL CAMIÓN Y REMOLQUE
     */
    async function cargarDatosAutocompletados() {
        const id = vehiculoSelect.value;
        if (!id) return;

        // Reset de sección remolque
        const seccionRemolque = document.getElementById('seccion-remolque');
        const inputRemolqueId = document.getElementById('id_remolque');
        const inputRemolquePatente = document.getElementById('remolque-patente');
        
        seccionRemolque.style.display = 'none'; 
        inputRemolqueId.value = ''; 
        inputRemolquePatente.value = '';

        try {
            const response = await fetch(`/mantenciones/api/datos-autocompletado/${id}/`);
            const data = await response.json();
            if (data.success) {
                const d = data.datos;
                document.getElementById('lugar-inspeccion').value = d.lugar_inspeccion;
                document.getElementById('conductor-nombre').value = d.conductor_nombre;
                document.getElementById('datos-autocompletados').style.display = 'flex';
                
                if (d.tiene_remolque) {
                    inputRemolquePatente.value = d.remolque_patente;
                    inputRemolqueId.value = d.remolque_id;
                    seccionRemolque.style.display = 'block';
                }

                // Si ya eligió tipo de inspección antes, recargamos para filtrar
                if (tipoSelect.value) cargarCategorias();
            }
        } catch (e) { 
            console.error("Error API Datos Autocompletado", e); 
        }
    }

    /**
     * FUNCIÓN: DIBUJAR EL CHECKLIST EN PANTALLA
     */
    function renderizarCategorias(categorias) {
        let html = `
            <div class="sticky-top bg-white pt-2 pb-3 shadow-sm mb-4 px-2" style="z-index: 1020; top: -1px;">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-bold text-primary small">PROGRESO REVISIÓN</span>
                    <span id="progreso-texto" class="badge rounded-pill bg-primary">0%</span>
                </div>
                <div class="progress" style="height: 12px; border-radius: 10px;">
                    <div id="checklist-progress" class="progress-bar progress-bar-striped progress-bar-animated bg-danger" 
                         role="progressbar" style="width: 0%;"></div>
                </div>
            </div>`;

        categorias.forEach(cat => {
            html += `
            <div class="card border-0 mb-4 shadow-sm" style="border-radius: 15px; overflow: hidden;">
                <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center py-3">
                    <h6 class="mb-0 fw-bold text-white">${cat.nombre}</h6>
                    <button type="button" class="btn btn-sm btn-light text-primary fw-bold" 
                            onclick="marcarCategoriaBuena('${cat.id}')">✓ TODO OK</button>
                </div>
                <div id="cat-body-${cat.id}" class="card-body p-0">`;
            
            cat.items.forEach((item, i) => {
                html += `
                <div class="checklist-row p-3 border-bottom">
                    <div class="item-info mb-2 fw-bold text-dark" style="font-size: 0.95rem;">
                        ${item.nombre} ${item.es_critico ? '<span class="text-danger">*</span>' : ''}
                    </div>
                    <div class="btn-group w-100" role="group">
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="b_${item.id}" value="B" data-item-id="${item.id}">
                        <label class="btn btn-outline-success py-2" for="b_${item.id}">BUENO</label>
                        
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="r_${item.id}" value="R" data-item-id="${item.id}">
                        <label class="btn btn-outline-warning py-2" for="r_${item.id}">REG.</label>
                        
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="m_${item.id}" value="M" data-item-id="${item.id}">
                        <label class="btn btn-outline-danger py-2" for="m_${item.id}">MALO</label>
                    </div>
                    <input type="text" class="form-control form-control-sm item-observacion mt-2" 
                           data-item-id="${item.id}" placeholder="Observación (opcional)">
                </div>`;
            });
            html += `</div></div>`;
        });

        checklistDiv.innerHTML = html;

        // Re-asignar eventos a los nuevos elementos creados
        document.querySelectorAll('.item-radio').forEach(radio => {
            radio.addEventListener('change', (e) => {
                actualizarChecklist();
                actualizarBarra();
                if (e.target.value === 'M' || e.target.value === 'R') {
                    const row = e.target.closest('.checklist-row');
                    const obs = row.querySelector('.item-observacion');
                    obs.classList.add('border-danger');
                    if(e.target.value === 'M') obs.focus();
                }
                if (window.navigator.vibrate) window.navigator.vibrate(10);
            });
        });

        document.querySelectorAll('.item-observacion').forEach(input => {
            input.addEventListener('input', actualizarChecklist);
        });
    }
});