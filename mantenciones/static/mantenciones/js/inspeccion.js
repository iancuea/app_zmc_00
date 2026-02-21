/**
 * FUNCIONES GLOBALES 
 * (Deben estar fuera para que los botones 'onclick' del HTML funcionen)
 */

function marcarCategoriaBuena(catId) {
    const container = document.getElementById(`cat-body-${catId}`);
    if (!container) return;

    // Marcamos todos los radios "B" (Bueno) de esta categoría
    container.querySelectorAll('input[value="B"]').forEach(radio => {
        radio.checked = true;
    });

    // Disparamos el evento 'change' manualmente para que el sistema sepa que se actualizó
    // Esto gatilla la actualización del JSON y de la barra de progreso
    const event = new Event('change', { bubbles: true });
    const primerRadio = container.querySelector('input[value="B"]');
    if (primerRadio) primerRadio.dispatchEvent(event);

    console.log(`Categoría ${catId} completada como OK`);
}

/**
 * LÓGICA DE INICIALIZACIÓN
 */
document.addEventListener('DOMContentLoaded', function() {
    const tipoInspeccionSelect = document.getElementById('id_tipo_inspeccion');
    const vehiculoSelect = document.getElementById('id_vehiculo');
    const categoriasChecklistDiv = document.getElementById('categorias-checklist');
    const resultadosChecklistInput = document.getElementById('resultados-checklist');
    const datosAutocompletadosDiv = document.getElementById('datos-autocompletados');
    const seccionRemolqueDiv = document.getElementById('seccion-remolque');
    const lugarInspeccionInput = document.getElementById('lugar-inspeccion');
    const conductorNombreInput = document.getElementById('conductor-nombre');
    const remolquePatenteInput = document.getElementById('remolque-patente');

    // Escuchar cambios principales
    if (tipoInspeccionSelect) tipoInspeccionSelect.addEventListener('change', cargarCategorias);
    if (vehiculoSelect) vehiculoSelect.addEventListener('change', cargarDatosAutocompletados);

    // Listener Inteligente: Auto-Foco en Observaciones si es R o M
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('item-radio')) {
            const itemId = e.target.dataset.itemId;
            const obsInput = document.querySelector(`.item-observacion[data-item-id="${itemId}"]`);
            
            if (e.target.value === 'M' || e.target.value === 'R') {
                obsInput.style.border = '2px solid #dc3545';
                obsInput.focus(); // Salto automático para escribir el problema
            } else {
                obsInput.style.border = '1px solid #ced4da';
            }
        }
    });

    async function cargarCategorias() {
        const tipo = tipoInspeccionSelect.value;
        if (!tipo) return;
        try {
            const response = await fetch(`/mantenciones/api/categorias/${tipo}/`);
            const data = await response.json();
            if (data.success) {
                renderizarCategorias(data.categorias);
            }
        } catch (error) { console.error('Error cargando categorías:', error); }
    }

    async function cargarDatosAutocompletados() {
        const camionId = vehiculoSelect.value;
        if (!camionId) return;
        try {
            const response = await fetch(`/mantenciones/api/datos-autocompletado/${camionId}/`);
            const data = await response.json();
            if (data.success) {
                const d = data.datos;
                lugarInspeccionInput.value = d.lugar_inspeccion || 'N/A';
                conductorNombreInput.value = d.conductor_nombre || 'N/A';
                datosAutocompletadosDiv.style.display = 'flex';
                if (d.tiene_remolque) {
                    remolquePatenteInput.value = d.remolque_patente;
                    seccionRemolqueDiv.style.display = 'block';
                } else {
                    seccionRemolqueDiv.style.display = 'none';
                }
                if (tipoInspeccionSelect.value) cargarCategorias();
            }
        } catch (error) { console.error('Error:', error); }
    }

   function renderizarCategorias(categorias) {
        let html = `
            <div class="sticky-progress mb-4 rounded-bottom">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-bold small text-primary">PROGRESO DE REVISIÓN</span>
                    <span id="porcentaje-txt" class="badge bg-primary">0%</span>
                </div>
                <div class="progress" style="height: 10px;">
                    <div id="checklist-progress" class="progress-bar bg-success progress-bar-striped" role="progressbar" style="width: 0%"></div>
                </div>
            </div>
        `;

        const totalDeItems = categorias.reduce((acc, c) => acc + c.items.length, 0);

        categorias.forEach(cat => {
            html += `
            <div class="card checklist-category-card">
                <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                    <span class="mb-0">${cat.nombre}</span>
                    <button type="button" class="btn btn-sm btn-light py-0" onclick="marcarCategoriaBuena('${cat.id}')">✓ TODO OK</button>
                </div>
                <div id="cat-body-${cat.id}" class="card-body p-0">`;
                
            cat.items.forEach((item, i) => {
                html += `
                <div class="checklist-row">
                    <div class="item-info text-uppercase">
                        <span class="text-muted me-2">${i + 1}.</span>${item.nombre}
                    </div>
                    
                    <div class="btn-group-mobile">
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="b_${item.id}" value="B" data-item-id="${item.id}">
                        <label class="btn btn-outline-success" for="b_${item.id}">B</label>
                        
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="r_${item.id}" value="R" data-item-id="${item.id}">
                        <label class="btn btn-outline-warning" for="r_${item.id}">R</label>
                        
                        <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="m_${item.id}" value="M" data-item-id="${item.id}">
                        <label class="btn btn-outline-danger" for="m_${item.id}">M</label>
                    </div>
                    
                    <input type="text" class="form-control item-observacion" data-item-id="${item.id}" placeholder="Nota si hay falla...">
                </div>`;
            });
            html += `</div></div>`;
        });

        document.getElementById('categorias-checklist').innerHTML = html;
        
        // Reconectar listeners
        document.querySelectorAll('.item-radio, .item-observacion').forEach(el => {
            el.addEventListener('change', () => {
                actualizarChecklist();
                actualizarBarraProgreso(totalDeItems);
            });
            if (el.type === 'text') el.addEventListener('input', actualizarChecklist);
        });
    }

        categoriasChecklistDiv.innerHTML = html;
        
        // Reconectar Listeners
        document.querySelectorAll('.item-radio, .item-observacion').forEach(el => {
            el.addEventListener('change', () => {
                actualizarChecklist();
                actualizarBarraProgreso(totalDeItems);
            });
            if (el.type === 'text') el.addEventListener('input', actualizarChecklist);
    });
    

    function actualizarBarraProgreso(totalItems) {
        const respondidos = document.querySelectorAll('.item-radio:checked').length;
        const porcentaje = Math.round((respondidos / totalItems) * 100);
        const bar = document.getElementById('checklist-progress');
        const txt = document.getElementById('porcentaje-txt');
        if (bar) bar.style.width = porcentaje + '%';
        if (txt) txt.innerText = porcentaje + '%';
    }

    function actualizarChecklist() {
        const resultados = [];
        document.querySelectorAll('.item-radio:checked').forEach(radio => {
            const itemId = radio.dataset.itemId;
            const obs = document.querySelector(`.item-observacion[data-item-id="${itemId}"]`).value;
            resultados.push({ item_id: itemId, estado: radio.value, observacion: obs });
        });
        resultadosChecklistInput.value = JSON.stringify(resultados);
    }

    // Botón Global de Llenado (Solo para desarrollo)
    window.llenarTodo = function() {
        document.querySelectorAll('input.item-radio[value="B"]').forEach(radio => radio.checked = true);
        document.getElementById('id_km_registro').value = "450000";
        actualizarChecklist();
        const total = document.querySelectorAll('.item-radio').length / 3;
        actualizarBarraProgreso(total);
    };
});