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

function gestionarErrorServidor() {
    const responsableInput = document.getElementById('id_responsable');
    const displayNombre = document.getElementById('nombre-responsable-modal');
    const kmInput = document.getElementById('id_km_registro');

    // 1. Extraer y formatear el primer nombre
    if (responsableInput && responsableInput.value && displayNombre) {
        const nombreCompleto = responsableInput.value.trim();
        const primerNombre = nombreCompleto.split(' ')[0];
        displayNombre.innerText = primerNombre.toUpperCase();
    }

    // 2. Inicializar y mostrar el modal de Bootstrap
    const modalEl = document.getElementById('modalError');
    if (modalEl) {
        const myModal = new bootstrap.Modal(modalEl);
        myModal.show();

        // 3. Al cerrar el modal, llevar al usuario al error (Scroll suave)
        modalEl.addEventListener('hidden.bs.modal', function () {
            // Buscamos cualquier alerta de error o el campo de KM si está marcado
            const errorElement = document.querySelector('.error-alert-box, .text-danger, .is-invalid');
            if (errorElement) {
                errorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                // Si el error es específicamente en el KM, le damos el foco al teclado
                if (kmInput && (kmInput.classList.contains('is-invalid') || kmInput.style.borderColor !== "")) {
                    kmInput.focus();
                }
            }
        });
    }

    // 4. Vibración de alerta (Opcional para móviles)
    if (navigator.vibrate) {
        navigator.vibrate([200, 100, 200]);
    }
}

// 1. VARIABLE GLOBAL PARA KM
let kmMinimoPermitido = 0;

document.addEventListener('DOMContentLoaded', function() {
    // 2. REFERENCIAS A ELEMENTOS DEL FORMULARIO
    const tipoSelect = document.getElementById('id_tipo_inspeccion');
    const vehiculoSelect = document.getElementById('id_vehiculo');
    const kmInput = document.getElementById('id_km_registro');

    // 3. LISTENERS DE CAMBIOS
    if (tipoSelect) tipoSelect.addEventListener('change', cargarCategorias);
    
    if (vehiculoSelect) {
        vehiculoSelect.addEventListener('change', function() {
            cargarDatosAutocompletados();
            if (this.value) mostrarPaso('#step-2');
        });
    }

    // --- VALIDACIÓN DE KM EN TIEMPO REAL ---
    if (kmInput) {
        kmInput.addEventListener('input', function() {
            if (this.value.length >= 3) mostrarPaso('#step-3');

            const kmIngresado = parseInt(this.value) || 0;
            const hint = document.getElementById('km-referencia-hint');
            
            if (hint && kmMinimoPermitido > 0) {
                if (kmIngresado > 0 && kmIngresado < kmMinimoPermitido) {
                    hint.style.color = "#e53e3e"; 
                    hint.style.fontWeight = "800";
                    this.style.borderColor = "#e53e3e";
                    this.style.backgroundColor = "#fff5f5";
                } else {
                    hint.style.color = "#718096";
                    hint.style.fontWeight = "600";
                    this.style.borderColor = ""; 
                    this.style.backgroundColor = "";
                }
            }
        });
    }

    // 4. LÓGICA DE RECUPERACIÓN TRAS ERROR (Mantiene el form abierto)
    if (vehiculoSelect && vehiculoSelect.value) {
        const step2 = document.getElementById('step-2');
        const step4 = document.getElementById('step-4');
        const datosAuto = document.getElementById('datos-autocompletados');

        if (step2) step2.style.display = 'block';
        if (step4) step4.style.display = 'block';
        if (datosAuto) datosAuto.style.display = 'flex';

        cargarDatosAutocompletados();
    }

    // 5. SCROLL AL ERROR
    const errorSiniestro = document.querySelector('.error-alert-box, .text-danger');
    if (errorSiniestro) {
        setTimeout(() => {
            errorSiniestro.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 800);
    }
});

/**
 * FUNCIONES (Viviendo fuera del listener principal para estabilidad)
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

async function cargarCategorias() {
    const tSel = document.getElementById('id_tipo_inspeccion');
    const vSel = document.getElementById('id_vehiculo');
    if (!tSel.value || !vSel.value) return; 

    try {
        const response = await fetch(`/mantenciones/api/categorias/${tSel.value}/`);
        const data = await response.json();
        if (data.success) {
            renderizarCategorias(data.categorias);
            mostrarPaso('#step-4');
        }
    } catch (e) { console.error("Error cargando items del checklist", e); }
}

async function cargarDatosAutocompletados() {
    const vSel = document.getElementById('id_vehiculo');
    const tSel = document.getElementById('id_tipo_inspeccion');
    const kmIn = document.getElementById('id_km_registro');
    
    if (!vSel || !vSel.value) return;

    const id = vSel.value;
    const seccionRemolque = document.getElementById('seccion-remolque');
    const inputRemolqueId = document.getElementById('id_remolque');
    const inputRemolquePatente = document.getElementById('remolque-patente');
    const hint = document.getElementById('km-referencia-hint');
    
    try {
        const response = await fetch(`/mantenciones/api/datos-autocompletado/${id}/`);
        const data = await response.json();
        
        if (data.success) {
            const d = data.datos;
            document.getElementById('lugar-inspeccion').value = d.lugar_inspeccion;
            document.getElementById('conductor-nombre').value = d.conductor_nombre;
            document.getElementById('datos-autocompletados').style.display = 'flex';
            
            kmMinimoPermitido = parseInt(d.km_actual_registrado) || 0;

            if (hint) {
                const kmFormateado = kmMinimoPermitido.toLocaleString('es-CL');
                hint.innerHTML = `📌 EL KM DEBE SER IGUAL O MAYOR A: <span style="color: var(--primary-zmc); font-weight: 800;">${kmFormateado} KM</span>`;
                // Reset visual al cargar nuevo vehículo
                hint.style.color = "#718096";
                hint.style.fontWeight = "600";
                kmIn.style.borderColor = "";
                kmIn.style.backgroundColor = "";
            }

            if (d.tiene_remolque) {
                inputRemolquePatente.value = d.remolque_patente;
                inputRemolqueId.value = d.remolque_id;
                seccionRemolque.style.display = 'block';
            } else {
                seccionRemolque.style.display = 'none';
            }

            // CARGA AUTOMÁTICA DE CATEGORÍAS SI YA HAY TIPO (Caso de error/recarga)
            if (tSel && tSel.value) cargarCategorias();
        }
    } catch (e) { console.error("Error API Datos Autocompletado", e); }
}

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
                <h6 class="mb-0">${cat.nombre}</h6>
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

    // RE-VINCULAR EVENTOS
    document.querySelectorAll('.item-radio').forEach(radio => {
        radio.addEventListener('change', () => {
            if (typeof actualizarChecklist === 'function') actualizarChecklist();
            if (typeof actualizarBarra === 'function') actualizarBarra();
        });
    });
    
    document.querySelectorAll('.item-observacion').forEach(input => {
        input.addEventListener('input', () => {
            if (typeof actualizarChecklist === 'function') actualizarChecklist();
        });
    });
}