"""
mantenciones/management/commands/enviar_alertas_preventivas.py

Comando Django que revisa la proyección predictiva de mantenciones
y envía un correo de alerta con los servicios que caen dentro de
los próximos 30 días.

Uso manual:
    python manage.py enviar_alertas_preventivas

Programado en Windows Task Scheduler para correr diariamente.
"""

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from datetime import date, timedelta

from core.models import Camion, EstadoCamion
from mantenciones.models import CicloEstadoCamion, CronogramaPlan


DESTINATARIO_PRUEBA = 'iancuevas7321@gmail.com'
DESTINATARIO_REAL   = 'bsantanav@gmail.com'

# Cambia a DESTINATARIO_REAL cuando termines de probar
DESTINATARIO_ACTIVO = DESTINATARIO_PRUEBA

KM_DIARIO_FALLBACK = 150.0
DIAS_ALERTA        = 30


class Command(BaseCommand):
    help = 'Envía alerta de mantenciones preventivas próximas (≤30 días)'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando revisión de mantenciones preventivas...')

        alertas = self._calcular_alertas()

        # DEBUG: ver qué encontró el motor
        self.stdout.write(f'Alertas encontradas: {len(alertas)}')
        for a in alertas:
            self.stdout.write(f"  → {a['patente']} | {a['plan']} | {a['dias']} días | {a['fecha']}")

        if not alertas:
            self.stdout.write(self.style.SUCCESS(
                'Sin mantenciones próximas en los siguientes 30 días. No se envió correo.'
            ))
            return

        self._enviar_correo(alertas)

    # ── MOTOR PREDICTIVO ────────────────────────────────────────────────────

    def _calcular_alertas(self):
        """
        Reutiliza la misma lógica del motor predictivo del Gantt.
        Devuelve solo los eventos que caen dentro de los próximos DIAS_ALERTA días.
        """
        hoy         = date.today()
        fecha_limite = hoy + timedelta(days=DIAS_ALERTA)
        alertas     = []

        camiones = (
            Camion.objects
            .filter(activo=True)
            .select_related('modelo', 'estado_actual', 'ciclo_estado')
        )

        # Cargar todos los planes en memoria (evita N+1)
        planes_raw = CronogramaPlan.objects.select_related('modelo').all()
        planes_por_modelo = {}
        for plan in planes_raw:
            mid = plan.modelo_id
            if mid not in planes_por_modelo:
                planes_por_modelo[mid] = {}
            planes_por_modelo[mid][plan.posicion_ciclo] = plan.paquetes_json

        for camion in camiones:
            estado = getattr(camion, 'estado_actual', None)
            ciclo  = getattr(camion, 'ciclo_estado',  None)

            if not estado or not ciclo or not camion.modelo_id:
                continue

            km_actual = float(estado.kilometraje or 0)
            if km_actual <= 0:
                continue

            # Tasa diaria real
            km_ganados = km_actual - ciclo.km_ultimo_servicio
            dias_trans = (
                (hoy - ciclo.fecha_ultimo_servicio).days
                if ciclo.fecha_ultimo_servicio else 0
            )
            if km_ganados > 0 and dias_trans > 0:
                km_diario = km_ganados / dias_trans
            else:
                km_diario = KM_DIARIO_FALLBACK
            km_diario = max(50.0, min(km_diario, 600.0))

            planes = planes_por_modelo.get(camion.modelo_id)
            if not planes:
                continue

            total_pos  = len(planes)
            intervalo  = float(camion.intervalo_mantencion or 20000)
            posicion   = ciclo.posicion_actual
            km_proximo = float(ciclo.km_ultimo_servicio) + intervalo

            if km_proximo < km_actual:
                km_proximo = km_actual + 1

            # Solo nos interesa el PRIMER evento de cada camión que caiga en la ventana
            while True:
                dias_hasta = (km_proximo - km_actual) / km_diario
                fecha_ev   = hoy + timedelta(days=dias_hasta)

                if fecha_ev > fecha_limite:
                    break  # Fuera de la ventana de 30 días, no hay más que revisar

                paquetes    = planes.get(posicion, ['SM?'])
                nombre_plan = ', '.join(paquetes)
                dias_restantes = (fecha_ev - hoy).days

                alertas.append({
                    'patente':       camion.patente,
                    'modelo':        camion.modelo.nombre if camion.modelo else '—',
                    'plan':          nombre_plan,
                    'fecha':         fecha_ev.strftime('%d/%m/%Y'),
                    'km_gatillo':    int(km_proximo),
                    'km_actual':     int(km_actual),
                    'km_diario':     round(km_diario, 1),
                    'dias':          dias_restantes,
                    'tipo_op':       camion.tipo_operacion,
                })

                # Avanzar para ver si el siguiente evento también cae en la ventana
                posicion   = (posicion % total_pos) + 1
                km_proximo += intervalo

        # Ordenar por días restantes (los más urgentes primero)
        alertas.sort(key=lambda x: x['dias'])
        return alertas

    # ── CORREO ──────────────────────────────────────────────────────────────

    def _enviar_correo(self, alertas):
        hoy      = date.today().strftime('%d/%m/%Y')
        n        = len(alertas)
        vencidos = [a for a in alertas if a['dias'] <= 0]
        proximos = [a for a in alertas if a['dias'] > 0]

        estado_txt = "VENCIDAS" if vencidos else "PROXIMAS"
        sujeto = f"ZMC Flota | {estado_txt} | {n} mantencion(es) preventiva(s) | {hoy}"

        html = self._construir_html(alertas, vencidos, proximos, hoy)

        # Fallback texto plano (para clientes que no renderizan HTML)
        texto_plano = (
            f"REPORTE MANTENCIONES PREVENTIVAS — {hoy}\n"
            f"Vencidas: {len(vencidos)} | Proximas: {len(proximos)}\n\n"
            + "\n".join(
                f"- {a['patente']} | {a['plan']} | {a['fecha']} | {a['dias']} dias"
                for a in alertas
            )
        )

        try:
            email = EmailMultiAlternatives(
                subject=sujeto,
                body=texto_plano,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[DESTINATARIO_ACTIVO],
            )
            email.attach_alternative(html, "text/html")
            email.send()
            self.stdout.write(self.style.SUCCESS(
                f'Correo HTML enviado a {DESTINATARIO_ACTIVO} con {n} alerta(s).'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al enviar correo: {e}'))


    def _construir_html(self, alertas, vencidos, proximos, hoy):
        """Construye el cuerpo HTML del correo con estilos inline."""

        def fila_tabla(a):
            if a['dias'] <= 0:
                bg     = '#fff5f5'
                badge  = '<span style="background:#E74C3C;color:#0E305D;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">VENCIDA</span>'
            elif a['dias'] <= 7:
                bg     = '#fffdf0'
                badge  = f'<span style="background:#F3C613;color:#0E305D;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">HOY +{a["dias"]}d</span>'
            else:
                bg     = '#f0f4fa'
                badge  = f'<span style="background:#0E305D;color:#0E305D;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">+{a["dias"]} días</span>'

            return f"""
            <tr style="background:{bg};">
                <td style="padding:10px 14px;font-family:monospace;font-size:14px;font-weight:bold;border-bottom:1px solid #e0e0e0;">{a['patente']}</td>
                <td style="padding:10px 14px;border-bottom:1px solid #e0e0e0;">{a['modelo']}</td>
                <td style="padding:10px 14px;border-bottom:1px solid #e0e0e0;">
                    <span style="font-family:monospace;font-weight:bold;font-size:13px;">{a['plan']}</span>
                </td>
                <td style="padding:10px 14px;border-bottom:1px solid #e0e0e0;">{a['fecha']}</td>
                <td style="padding:10px 14px;border-bottom:1px solid #e0e0e0;font-family:monospace;">{a['km_gatillo']:,} km</td>
                <td style="padding:10px 14px;border-bottom:1px solid #e0e0e0;font-family:monospace;">{a['km_actual']:,} km</td>
                <td style="padding:10px 14px;border-bottom:1px solid #e0e0e0;">{badge}</td>
            </tr>"""

        filas = "\n".join(fila_tabla(a) for a in alertas)

        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif;font-size:14px;color:#2c3e50;">

        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:720px;margin:24px auto;">

            <!-- HEADER -->
            <tr>
                <td style="background:#0E305D;padding:20px 28px;border-radius:8px 8px 0 0;">
                    <span style="color:#0E305D;font-size:18px;font-weight:bold;letter-spacing:0.5px;">
                        Panel Predictivo ZMC
                    </span>
                    <br>
                    <span style="color:#7a9cc0;font-size:12px;font-family:monospace;">
                        Flota Magallanes · Reporte del {hoy}
                    </span>
                </td>
            </tr>

            <!-- RESUMEN EJECUTIVO -->
            <tr>
                <td style="background:#ffffff;padding:20px 28px;border-left:1px solid #e0e0e0;border-right:1px solid #e0e0e0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td width="33%" style="padding:0 6px 0 0;">
                                <div style="background:#fdf0f0;border:1px solid #f5bcbc;border-radius:6px;padding:14px;text-align:center;">
                                    <div style="font-size:32px;font-weight:bold;color:#E74C3C;line-height:1;">{len(vencidos)}</div>
                                    <div style="font-size:11px;color:#a93226;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Vencidas</div>
                                </div>
                            </td>
                            <td width="33%" style="padding:0 3px;">
                                <div style="background:#fffdf0;border:1px solid #f5e070;border-radius:6px;padding:14px;text-align:center;">
                                    <div style="font-size:32px;font-weight:bold;color:#d68910;line-height:1;">{len(proximos)}</div>
                                    <div style="font-size:11px;color:#7a6000;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Próximas ≤ 30d</div>
                                </div>
                            </td>
                            <td width="33%" style="padding:0 0 0 6px;">
                                <div style="background:#f0f4fa;border:1px solid #b0c4de;border-radius:6px;padding:14px;text-align:center;">
                                    <div style="font-size:32px;font-weight:bold;color:#0E305D;line-height:1;">{len(alertas)}</div>
                                    <div style="font-size:11px;color:#0a2444;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;">Total alertas</div>
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>

            <!-- TABLA DETALLE -->
            <tr>
                <td style="background:#ffffff;padding:0 28px 24px 28px;border-left:1px solid #e0e0e0;border-right:1px solid #e0e0e0;">
                    <p style="font-size:12px;font-weight:bold;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.6px;margin:0 0 10px 0;">
                        Detalle por unidad
                    </p>
                    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #e0e0e0;border-radius:6px;overflow:hidden;">
                        <thead>
                            <tr style="background:#f8f9fa;">
                                <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;">Unidad</th>
                                <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;">Modelo</th>
                                <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;">Servicio</th>
                                <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;">Fecha est.</th>
                                <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;">Km gatillo</th>
                                <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;">Km actual</th>
                                <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;">Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas}
                        </tbody>
                    </table>
                </td>
            </tr>

            <!-- FOOTER -->
            <tr>
                <td style="background:#f8f9fa;padding:14px 28px;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px;text-align:center;">
                    <span style="font-size:11px;color:#aab0b8;">
                        Generado automáticamente por app_zmc · Sistema de Gestión de Flota ZMC · Magallanes
                    </span>
                </td>
            </tr>

        </table>
        </body>
        </html>
        """

    def _bloque_alerta(self, a):
        dias_txt = "HOY (VENCIDA)" if a['dias'] <= 0 else f"en {a['dias']} día(s)"
        return [
            f"  Unidad    : {a['patente']} ({a['modelo']} · {a['tipo_op']})",
            f"  Servicio  : {a['plan']}",
            f"  Fecha est.: {a['fecha']} — {dias_txt}",
            f"  Km gatillo: {a['km_gatillo']:,} km",
            f"  Km actual : {a['km_actual']:,} km",
            f"  Uso diario: {a['km_diario']} km/día (promedio)",
            "",
        ]