/**
 * FUNCIONES GLOBALES
 */
function marcarCategoriaBuena(catId) {
    const container = document.getElementById(`cat-body-${catId}`);
    if (!container) return;

    const radiosB = container.querySelectorAll('input[value="B"]');
    radiosB.forEach(radio => {
        radio.checked = true;
    });

    // Feedback visual rápido
    container.style.backgroundColor = 'rgba(16, 185, 129, 0.05)';
    setTimeout(() => container.style.backgroundColor = 'transparent', 500);

    // Disparar evento para actualizar JSON y Barra
    if (radiosB.length > 0) {
        const event = new Event('change', { bubbles: true });
        radiosB[0].dispatchEvent(event);
    }
    
    // Vibración suave (haptic feedback)
    if (window.navigator.vibrate) window.navigator.vibrate(20);

    actualizarChecklist();
    actualizarBarra();
}

/**
 * INICIALIZACIÓN
 */
document.addEventListener('DOMContentLoaded', function() {
    const tipoSelect = document.getElementById('id_tipo_inspeccion');
    const vehiculoSelect = document.getElementById('id_vehiculo');
    const checklistDiv = document.getElementById('categorias-checklist');
    const resultadosInput = document.getElementById('resultados-checklist');

    if (tipoSelect) tipoSelect.addEventListener('change', cargarCategorias);
    if (vehiculoSelect) vehiculoSelect.addEventListener('change', cargarDatosAutocompletados);

    // Función para mostrar con animación suave
    function mostrarPaso(selector) {
        const el = document.querySelector(selector);
        if (el && el.style.display === 'none') {
            el.style.opacity = 0;
            el.style.display = 'block';
            setTimeout(() => {
                el.style.transition = 'opacity 0.5s ease';
                el.style.opacity = 1;
            }, 10);
        }
    }

    // 1. Escuchar cambios en Patente para mostrar Paso 2
    document.getElementById('id_vehiculo').addEventListener('change', function() {
        if (this.value) mostrarPaso('#step-2');
    });

    // 2. Escuchar cambios en KM para mostrar Paso 3
    document.getElementById('id_km_registro').addEventListener('input', function() {
        if (this.value.length >= 3) mostrarPaso('#step-3');
    });

    // Listener inteligente para Auto-Foco y Colores
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('item-radio')) {
            const itemId = e.target.dataset.itemId;
            const row = e.target.closest('.checklist-row');
            const obsInput = row.querySelector('.item-observacion');
            
            // Vibrar al tocar
            if (window.navigator.vibrate) window.navigator.vibrate(10);

            // Si es Malo o Regular, destacar y enfocar
            if (e.target.value === 'M' || e.target.value === 'R') {
                obsInput.classList.add('border-danger');
                if(e.target.value === 'M') obsInput.focus();
            } else {
                obsInput.classList.remove('border-danger');
            }
        }
    });

    async function cargarCategorias() {
        const tipo = tipoSelect.value;
        const vehiculo = vehiculoSelect.value;
        
        // Solo disparamos la carga si ambos campos están llenos
        if (!tipo || !vehiculo) return; 

        try {
            const response = await fetch(`/mantenciones/api/categorias/${tipo}/`);
            const data = await response.json();
            if (data.success) {
                renderizarCategorias(data.categorias);
                // Mostramos el paso 4 explícitamente por si acaso
                document.getElementById('step-4').style.display = 'block';
            }
        } catch (e) { console.error("Error cargando items", e); }
    }

    async function cargarDatosAutocompletados() {
        const id = vehiculoSelect.value;
        if (!id) return;
        // --- RESETEO DE ESTADOS ---
        // Escondemos el remolque por defecto antes de verificar el nuevo camión
        const seccionRemolque = document.getElementById('seccion-remolque');
        const inputRemolqueId = document.getElementById('id_remolque');
        const inputRemolquePatente = document.getElementById('remolque-patente');
        
        seccionRemolque.style.display = 'none'; 
        inputRemolqueId.value = ''; // Limpiamos el valor para que no se envíe el remolque anterior
        inputRemolquePatente.value = '';
        try {
            const response = await fetch(`/mantenciones/api/datos-autocompletado/${id}/`);
            const data = await response.json();
            if (data.success) {
                const d = data.datos;
                document.getElementById('lugar-inspeccion').value = d.lugar_inspeccion;
                document.getElementById('conductor-nombre').value = d.conductor_nombre;
                document.getElementById('datos-autocompletados').style.display = 'flex';
                // --- LÓGICA CONDICIONAL ---
                if (d.tiene_remolque) {
                    inputRemolquePatente.value = d.remolque_patente;
                    inputRemolqueId.value = d.remolque_id; // Asegúrate de que la API envíe el ID
                    seccionRemolque.style.display = 'block';
                }

                // Si ya hay un tipo de inspección elegido, recargar las categorías
                if (tipoSelect.value) cargarCategorias();
                }
        } catch (e) { console.error("Error API Datos", e); }
    }

    function renderizarCategorias(categorias) {
        // 1. DESBLOQUEAR PASO 4: Mostrar el contenedor que estaba oculto
        const step4 = document.getElementById('step-4');
        const checklistDiv = document.getElementById('categorias-checklist');
        
        if (step4) {
            step4.style.display = 'block';
            setTimeout(() => { step4.style.opacity = '1'; }, 10);
        }

        // 2. CONSTRUIR EL HTML
        let html = `
            <div class="sticky-progress mb-4">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="fw-800 text-primary small">ESTADO DE REVISIÓN</span>
                    <span id="progreso-texto" class="badge rounded-pill bg-primary">0%</span>
                </div>
                <div class="progress" style="height: 14px; border-radius: 20px; background: #e2e8f0;">
                    <div id="checklist-progress" class="progress-bar progress-bar-striped progress-bar-animated bg-success" 
                        role="progressbar" style="width: 0%; transition: width 0.5s ease;"></div>
                </div>
            </div>`;

        const totalItems = categorias.reduce((acc, c) => acc + c.items.length, 0);

        categorias.forEach(cat => {
            html += `
            <div class="card checklist-category-card border-0 mb-4 shadow-sm">
                <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center py-3">
                    <h6 class="mb-0 fw-bold text-white px-2">${cat.nombre}</h6>
                    <button type="button" class="btn btn-sm btn-light text-primary fw-bold shadow-sm" 
                            style="border-radius: 8px; font-size: 0.7rem;"
                            onclick="marcarCategoriaBuena('${cat.id}')">
                        ✓ TODO OK
                    </button>
                </div>
                <div id="cat-body-${cat.id}" class="card-body p-2">`;
            
            cat.items.forEach((item, i) => {
                html += `
                <div class="checklist-row p-3 border-bottom">
                    <div class="item-info mb-2 fw-bold text-dark" style="font-size: 0.9rem;">
                        <span class="text-muted small me-1">${i + 1}.</span> ${item.nombre}
                    </div>
                    <div class="btn-group-mobile">
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="b_${item.id}" value="B" data-item-id="${item.id}">
                        <label class="btn btn-outline-success" for="b_${item.id}">BUENO</label>
                        
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="r_${item.id}" value="R" data-item-id="${item.id}">
                        <label class="btn btn-outline-warning" for="r_${item.id}">REG.</label>
                        
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="m_${item.id}" value="M" data-item-id="${item.id}">
                        <label class="btn btn-outline-danger" for="m_${item.id}">MALO</label>
                    </div>
                    <input type="text" class="form-control form-control-sm item-observacion mt-2" 
                        data-item-id="${item.id}" placeholder="Escribe el hallazgo aquí...">
                </div>`;
            });
            html += `</div></div>`;
        });

        // 3. INYECTAR Y AUTO-SCROLL
        checklistDiv.innerHTML = html;
        
        // Hace que el celular baje solo hasta donde empezaron los items
        checklistDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // 4. REASIGNAR LISTENERS
        document.querySelectorAll('.item-radio, .item-observacion').forEach(el => {
            el.addEventListener('change', () => {
                actualizarChecklist();
                actualizarBarra(); // Llamamos a la versión que cuenta todo el DOM
            });
            // Para que guarde mientras escribe en las observaciones
            if (el.type === 'text') {
                el.addEventListener('input', actualizarChecklist);
            }
        });
    }

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
            
            // Colores dinámicos
            if (perc < 40) {
                bar.className = "progress-bar progress-bar-striped progress-bar-animated bg-danger";
            } else if (perc < 99) {
                bar.className = "progress-bar progress-bar-striped progress-bar-animated bg-warning";
            } else {
                bar.className = "progress-bar bg-success"; // Verde sólido al terminar
                if (window.navigator.vibrate) window.navigator.vibrate([30, 50, 30]); // Vibración especial de éxito
            }
        }
    }

    function actualizarChecklist() {
        const res = [];
        document.querySelectorAll('.item-radio:checked').forEach(r => {
            const id = r.dataset.itemId;
            const obs = document.querySelector(`.item-observacion[data-item-id="${id}"]`).value;
            res.push({ item_id: id, estado: r.value, observacion: obs });
        });
        resultadosInput.value = JSON.stringify(res);
    }
});