/**
 * Renderiza la lista de motivos o un check de éxito si no hay alertas.
 */
function renderizarMotivos(lista, documentos = []) {
    let htmlContent = "";

    // 1. Renderizar Alertas/Motivos
    if (!lista || lista.length === 0) {
        htmlContent += '<span style="color: #10b981; font-size: 0.8rem; font-weight: 600;">✅ Sin alertas</span>';
    } else {
        htmlContent += `<ul style="margin:0; padding-left:15px; font-size: 0.82rem; line-height: 1.4;">
                            ${lista.map(m => `<li>${m}</li>`).join("")}
                        </ul>`;
    }

    // 2. NUEVO: Renderizar Documentos de Drive
    if (documentos && documentos.length > 0) {
        htmlContent += `<div class="drive-docs-container" style="margin-top: 8px; border-top: 1px dotted #ccc; padding-top: 5px;">`;
        documentos.forEach(doc => {
            htmlContent += `
                <a href="${doc.ruta}" target="_blank" title="Ver ${doc.nombre}"
                   style="font-size: 0.75rem; color: #004a99; text-decoration: none; display: flex; align-items: center; gap: 5px; margin-bottom: 4px; font-weight: bold;">
                    <span style="font-size: 1rem;">📄</span> ${doc.nombre}
                </a>`;
        });
        htmlContent += `</div>`;
    }

    const necesitaBoton = lista && lista.length > 2;
    let finalHtml = `<div class="motivos-container">${htmlContent}</div>`;
    
    if (necesitaBoton) {
        finalHtml += `<button class="btn-ver-alertas" onclick="toggleAlertas(this)">Ver todas (${lista.length})</button>`;
    }
    
    return finalHtml;
}

/**
 * Carga y sincroniza los estados de toda la flota (Tractos y Remolques)
 */
fetch("/api/camiones/estado/")
    .then(res => {
        if (!res.ok) throw new Error("Error en servidor");
        return res.json();
    })
    .then(data => {
        data.forEach(item => {
            // --- 1. PROCESAR TRACTO (CAMIÓN) ---
            const filaCamion = document.querySelector(`tr[data-camion-id="${item.id_camion}"]`);
            if (filaCamion) {
                // Sincronizar clases de color
                filaCamion.classList.remove("estado-vencida", "estado-critica", "estado-ok");
                if (item.css) filaCamion.classList.add(item.css);
                
                // Actualizar texto de la columna Mecánica
                const elLabel = filaCamion.querySelector(".health-indicator strong");
                if (elLabel) elLabel.innerText = item.estado;

                // Inyectar Motivos del Tracto
                const tdMot = filaCamion.querySelector(".motivos");
                if (tdMot) tdMot.innerHTML = renderizarMotivos(item.motivos, item.documentos);
            }

            // --- 2. PROCESAR REMOLQUE VINCULADO ---
            if (item.id_remolque) {
                const filaRem = document.querySelector(`tr[data-remolque-id="${item.id_remolque}"]`);
                if (filaRem) {
                    // Sincronizar clases de color del remolque
                    filaRem.classList.remove("estado-vencida", "estado-critica", "estado-ok");
                    if (item.estado_remolque_css) filaRem.classList.add(item.estado_remolque_css);

                    // Actualizar texto de estado del remolque (ej: de OK a VENCIDA)
                    const tdEstadoRem = filaRem.querySelector(".estado-mantencion-texto-rem");
                    if (tdEstadoRem) {
                        const labelSimple = item.estado_remolque_css.replace('estado-', '').toUpperCase();
                        tdEstadoRem.innerText = labelSimple;
                    }

                    // INYECTAR MOTIVOS DEL REMOLQUE (Aquí es donde aparecían los documentos)
                    const tdMotRem = filaRem.querySelector(".motivos-remolque");
                    if (tdMotRem) {
                        // Forzamos el renderizado de la lista que viene en 'motivos_remolque'
                        tdMotRem.innerHTML = renderizarMotivos(item.motivos_remolque, item.documentos_remolque);
                    }
                }
            }
        });
        console.log("Sincronización de motivos completada.");
    })
    .catch(err => {
        console.error("Error API:", err);
        document.querySelectorAll(".loader-dots").forEach(el => el.innerText = "⚠️ Error");
    });

window.toggleAlertas = function(btn) {
    console.log("Botón presionado"); // Si ves esto en la consola, el JS cargó bien
    
    const celda = btn.closest('td');
    const container = celda.querySelector('.motivos-container');
    const fila = btn.closest('tr');
    
    if (container && fila) {
        const isExpanded = container.classList.toggle('expanded');
        fila.classList.toggle('expanded');
        
        btn.innerText = isExpanded ? 'VER MENOS' : `VER TODAS (${container.querySelectorAll('li').length})`;
        
        // Ajuste de scroll suave si la lista es muy larga
        if (isExpanded) {
            btn.style.bottom = "10px";
        } else {
            btn.style.bottom = "5px";
        }
    }
};