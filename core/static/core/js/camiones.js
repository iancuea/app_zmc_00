/**
 * Función para renderizar motivos en listas
 */
function renderizarMotivos(lista) {
    if (!lista || lista.length === 0) return '<span class="text-muted">Sin observaciones</span>';
    return `<ul style="margin:0; padding-left:15px; font-size: 0.85rem;">${lista.map(m => `<li>${m}</li>`).join("")}</ul>`;
}

/**
 * Carga de estados desde la API
 */
fetch("/api/camiones/estado/")
    .then(res => {
        if (!res.ok) throw new Error("Error en la respuesta del servidor");
        return res.json();
    })
    .then(data => {
        data.forEach(item => {
            // --- 🚜 TRACTO (CAMIÓN) ---
            const filaCamion = document.querySelector(`tr[data-camion-id="${item.id_camion}"]`);
            if (filaCamion) {
                // Limpieza total de clases de estado previas
                filaCamion.classList.remove(
                    "estado-vencida", "estado-critica", "estado-ok", 
                    "estado-danger", "estado-warning"
                );

                // USAMOS DIRECTAMENTE EL CSS QUE VIENE DEL BACKEND (item.css)
                // Esto garantiza que el color en el JS sea IGUAL al del HTML inicial
                if (item.css) {
                    filaCamion.classList.add(item.css);
                }
                
                // Inyectar Motivos en la celda correspondiente
                const tdMot = filaCamion.querySelector(".motivos");
                if (tdMot) {
                    tdMot.innerHTML = renderizarMotivos(item.motivos);
                }
            }

            // --- 🚛 REMOLQUE ---
            if (item.id_remolque) {
                const filaRem = document.querySelector(`tr[data-remolque-id="${item.id_remolque}"]`);
                if (filaRem) {
                    filaRem.classList.remove(
                        "estado-vencida", "estado-critica", "estado-ok",
                        "estado-danger", "estado-warning"
                    );
                    
                    // Usamos el CSS que calculó el backend para el remolque
                    if (item.estado_remolque_css) {
                        filaRem.classList.add(item.estado_remolque_css);
                    }

                    const tdMotRem = filaRem.querySelector(".motivos-remolque");
                    if (tdMotRem) {
                        tdMotRem.innerHTML = renderizarMotivos(item.motivos_remolque);
                    }
                }
            }
        });
        console.log("Sincronización de flota completada.");
    })
    .catch(err => {
        console.error("Error al sincronizar estados:", err);
        // Opcional: mostrar un mensaje visual en la tabla si falla la carga
        document.querySelectorAll(".loader-dots").forEach(el => {
            el.innerHTML = '<span class="text-danger">Error de conexión</span>';
        });
    });