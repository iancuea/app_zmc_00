/**
 * Función para renderizar motivos en listas
 */
function renderizarMotivos(lista) {
    if (!lista || lista.length === 0) return "Sin observaciones";
    return `<ul style="margin:0; padding-left:15px;">${lista.map(m => `<li>${m}</li>`).join("")}</ul>`;
}

/**
 * Carga de estados desde la API
 */
fetch("/api/camiones/estado/")
    .then(res => res.json())
    .then(data => {
        data.forEach(item => {
            // --- 🚜 TRACTO (CAMIÓN) ---
            const filaCamion = document.querySelector(`tr[data-camion-id="${item.id_camion}"]`);
            if (filaCamion) {
                // Limpieza total
                filaCamion.classList.remove(
                    "estado-vencida", "estado-vencido", "estado-danger",
                    "estado-critica", "estado-critico", "estado-warning",
                    "estado-ok", "estado-muted"
                );

                // Mapeo de clases (Aseguramos que coincida con tu CSS)
                let claseFinal = "estado-ok";
                if (item.estado === "VENCIDA") claseFinal = "estado-danger";
                else if (item.estado === "CRITICA") claseFinal = "estado-warning";
                
                filaCamion.classList.add(claseFinal);
                
                // Inyectar Motivos
                const tdMot = filaCamion.querySelector(".motivos");
                if (tdMot) tdMot.innerHTML = renderizarMotivos(item.motivos);
            }

            // --- 🚛 REMOLQUE ---
            if (item.id_remolque) {
                const filaRem = document.querySelector(`tr[data-remolque-id="${item.id_remolque}"]`);
                if (filaRem) {
                    filaRem.classList.remove("estado-danger", "estado-warning", "estado-ok", "estado-vencida");
                    
                    // Usamos el CSS que ya calculó el backend
                    if (item.estado_remolque_css) {
                        // Traducimos estado-vencida a estado-danger si es necesario
                        let cssRem = item.estado_remolque_css.toLowerCase();
                        if (cssRem === "estado-vencida") cssRem = "estado-danger";
                        filaRem.classList.add(cssRem);
                    }

                    const tdMotRem = filaRem.querySelector(".motivos-remolque");
                    if (tdMotRem) tdMotRem.innerHTML = renderizarMotivos(item.motivos_remolque);
                }
            }
        });
    })
    .catch(err => console.error("Error al sincronizar estados:", err));