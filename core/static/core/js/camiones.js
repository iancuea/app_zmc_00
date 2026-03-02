/**
 * Renderiza la lista de motivos o un check de éxito si no hay alertas.
 */
function renderizarMotivos(lista) {
    // Si la lista es null o vacía, mostramos que todo está al día
    if (!lista || lista.length === 0) {
        return '<span style="color: #10b981; font-size: 0.8rem; font-weight: 600;">✅ Sin alertas pendientes</span>';
    }
    // Si hay motivos, los listamos con viñetas
    return `<ul style="margin:0; padding-left:15px; font-size: 0.82rem; line-height: 1.2;">
        ${lista.map(m => `<li>${m}</li>`).join("")}
    </ul>`;
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
                if (tdMot) tdMot.innerHTML = renderizarMotivos(item.motivos);
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
                        tdMotRem.innerHTML = renderizarMotivos(item.motivos_remolque);
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