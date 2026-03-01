/**
 * FUNCIONES GLOBALES
 */
function actualizarBarra() {
    const total = document.querySelectorAll('.checklist-row').length;
    let respondidos = 0;

    document.querySelectorAll('.checklist-row').forEach(row => {
        const radioMarcado = row.querySelector('.item-radio:checked');
        const switchAplica = row.querySelector('.switch-aplica');

        // Un ítem está "listo" si tiene un radio marcado O si el switch está apagado (N/A)
        if (radioMarcado || (switchAplica && !switchAplica.checked)) {
            respondidos++;
        }
    });
    
    if (total === 0) return;

    const perc = Math.round((respondidos / total) * 100);
    const bar = document.getElementById('checklist-progress');
    const texto = document.getElementById('progreso-texto');

    if (bar && texto) {
        bar.style.width = perc + '%';
        texto.innerText = perc + '%';
        
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
    
    // IMPORTANTE: Buscamos todas las filas, no solo los seleccionados
    document.querySelectorAll('.checklist-row').forEach(row => {
        const radioMarcado = row.querySelector('.item-radio:checked');
        const switchAplica = row.querySelector('.switch-aplica');
        const obsInput = row.querySelector('.item-observacion');
        
        // Buscamos el ID del item de cualquier radio en la fila
        const primerRadio = row.querySelector('.item-radio');
        if (!primerRadio) return;
        const id = primerRadio.dataset.itemId;

        let estado = "";
        
        // SI EL SWITCH ESTÁ APAGADO -> FORZAMOS "NA"
        if (switchAplica && !switchAplica.checked) {
            estado = "X"; 
        } else if (radioMarcado) {
            estado = radioMarcado.value;
        }

        res.push({ 
            item_id: id, 
            estado: estado, 
            observacion: obsInput ? obsInput.value : '' 
        });
    });
    
    if (resultadosInput) {
        resultadosInput.value = JSON.stringify(res);
        console.log("JSON a enviar:", resultadosInput.value); // Mira esto en la consola del navegador (F12)
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
            document.getElementById('conductor-nombre').value = d.conductor_nombre_corto || d.conductor_nombre;
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
            // 1. DEFINICIÓN DE BOTONES SEGÚN TIPO_RESPUESTA
            let botonesHtml = "";
            if (item.tipo_respuesta === 'BINARIO') {
                botonesHtml = `
                    <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="s_${item.id}" value="S" data-item-id="${item.id}">
                    <label class="btn btn-outline-success" for="s_${item.id}">SÍ</label>
                    <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="n_${item.id}" value="N" data-item-id="${item.id}">
                    <label class="btn btn-outline-danger" for="n_${item.id}">NO</label>
                `;
            } else {
                botonesHtml = `
                    <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="b_${item.id}" value="B" data-item-id="${item.id}">
                    <label class="btn btn-outline-success" for="b_${item.id}">BUENO</label>
                    <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="r_${item.id}" value="R" data-item-id="${item.id}">
                    <label class="btn btn-outline-warning" for="r_${item.id}">REG.</label>
                    <input type="radio" class="btn-check item-radio" name="item_${item.id}" id="m_${item.id}" value="M" data-item-id="${item.id}">
                    <label class="btn btn-outline-danger" for="m_${item.id}">MALO</label>
                `;
            }

            // 2. DEFINICIÓN DEL SWITCH SI EL ÍTEM ES OPCIONAL
            let switchHtml = "";
            if (item.es_opcional) {
                switchHtml = `
                    <div class="form-check form-switch mb-2 mt-1">
                        <input class="form-check-input switch-aplica" type="checkbox" 
                               id="sw_${item.id}" data-item-id="${item.id}" checked>
                        <label class="form-check-label small text-muted fw-bold" for="sw_${item.id}" style="font-size: 0.75rem;">
                            ESTE EQUIPO CUENTA CON ESTE COMPONENTE
                        </label>
                    </div>
                `;
            }

            // 3. CONSTRUCCIÓN DEL HTML FINAL DEL ÍTEM
            html += `
            <div class="checklist-row px-2 py-3 border-bottom" id="row_${item.id}">
                <div class="item-info mb-1" style="font-weight: 700; color: #2d3748;">
                    ${item.nombre} ${item.es_critico ? '<span class="text-danger">*</span>' : ''}
                </div>

                ${switchHtml}

                <div class="btn-group-mobile" id="cont_botones_${item.id}" style="transition: opacity 0.3s ease;">
                    ${botonesHtml}
                </div>
                
                <input type="text" class="form-control item-observacion mt-2" 
                    id="obs_${item.id}" 
                    data-item-id="${item.id}" 
                    placeholder="Escribe el hallazgo aquí..."
                    style="border-radius: 8px; font-size: 0.85rem;">
            </div>`;
        });
        html += `</div></div>`;
    });

    checklistDiv.innerHTML = html;

    // RE-VINCULAR EVENTOS
// 1. LISTENERS PARA RADIOS (BUENO/REG/MAL o SÍ/NO)
    document.querySelectorAll('.item-radio').forEach(radio => {
        radio.addEventListener('change', () => {
            if (typeof actualizarChecklist === 'function') actualizarChecklist();
            if (typeof actualizarBarra === 'function') actualizarBarra();
        });
    });
    
    // 2. LISTENERS PARA OBSERVACIONES (HALLAZGOS)
    document.querySelectorAll('.item-observacion').forEach(input => {
        input.addEventListener('input', () => {
            if (typeof actualizarChecklist === 'function') actualizarChecklist();
        });
    });

    // 3. LISTENERS PARA SWITCHES (APLICA / NO APLICA)
    document.querySelectorAll('.switch-aplica').forEach(sw => {
        sw.addEventListener('change', function() {
            const itemId = this.dataset.itemId;
            const contBotones = document.getElementById(`cont_botones_${itemId}`);
            const inputObs = document.getElementById(`obs_${itemId}`);
            
            if (!this.checked) {
                // ESTADO: NO APLICA
                if (contBotones) {
                    contBotones.style.opacity = "0.3";
                    contBotones.style.pointerEvents = "none";
                }
                if (inputObs) {
                    inputObs.value = "N/A - El equipo no cuenta con este componente";
                    inputObs.readOnly = true;
                    inputObs.style.backgroundColor = "#f7fafc"; // Gris claro para indicar bloqueo
                }
                
                // Desmarcar cualquier opción seleccionada anteriormente
                document.querySelectorAll(`input[name="item_${itemId}"]`).forEach(r => {
                    r.checked = false;
                });
            } else {
                // ESTADO: APLICA (Vuelve a la normalidad)
                if (contBotones) {
                    contBotones.style.opacity = "1";
                    contBotones.style.pointerEvents = "auto";
                }
                if (inputObs) {
                    inputObs.value = "";
                    inputObs.readOnly = false;
                    inputObs.style.backgroundColor = "#ffffff";
                }
            }
            
            // Forzamos actualización para que la barra de progreso y el JSON de resultados se enteren
            if (typeof actualizarChecklist === 'function') actualizarChecklist();
            if (typeof actualizarBarra === 'function') actualizarBarra();
        });
    });
}