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
        const checklistDiv = document.getElementById('categorias-checklist');
        let html = `
            <div class="sticky-progress">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="fw-800 text-primary small" style="font-weight: 800;">ESTADO DE REVISIÓN</span>
                    <span id="progreso-texto" class="badge rounded-pill bg-primary">0%</span>
                </div>
                <div class="progress" style="height: 14px; border-radius: 20px; background: #e2e8f0;">
                    <div id="checklist-progress" class="progress-bar progress-bar-striped progress-bar-animated bg-success" 
                        role="progressbar" style="width: 0%; transition: width 0.5s ease;"></div>
                </div>
            </div>`;

        categorias.forEach(cat => {
            html += `
            <div class="card info-card-modern mb-4">
                <div class="card-header bg-primary text-white">
                    <h6>${cat.nombre}</h6>
                    <button type="button" class="btn btn-sm btn-light text-primary fw-bold" 
                            style="border-radius: 8px; font-size: 0.7rem; padding: 5px 15px;"
                            onclick="marcarCategoriaBuena('${cat.id}')">
                        ✓ TODO OK
                    </button>
                </div>
                <div id="cat-body-${cat.id}" class="info-card-content">`;
            
            cat.items.forEach((item) => {
                html += `
                <div class="checklist-row">
                    <div class="item-info">
                        ${item.nombre} ${item.es_critico ? '<span class="text-danger">*</span>' : ''}
                    </div>
                    
                    <div class="btn-group-mobile">
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="b_${item.id}" value="B" data-item-id="${item.id}">
                        <label class="btn btn-outline-success" for="b_${item.id}">BUENO</label>
                        
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="r_${item.id}" value="R" data-item-id="${item.id}">
                        <label class="btn btn-outline-warning" for="r_${item.id}">REG.</label>
                        
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="m_${item.id}" value="M" data-item-id="${item.id}">
                        <label class="btn btn-outline-danger" for="m_${item.id}">MALO</label>
                    </div>
                    
                    <input type="text" class="form-control item-observacion" 
                        data-item-id="${item.id}" placeholder="Escribe el hallazgo aquí...">
                </div>`;
            });
            html += `</div></div>`;
        });

        checklistDiv.innerHTML = html;

        // 3. Re-vincular eventos para que la barra y el JSON funcionen
        document.querySelectorAll('.item-radio').forEach(radio => {
            radio.addEventListener('change', () => {
                actualizarChecklist();
                actualizarBarra();
            });
        });
        
        document.querySelectorAll('.item-observacion').forEach(input => {
            input.addEventListener('input', actualizarChecklist);
        });
    }
});