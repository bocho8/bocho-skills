#!/usr/bin/env python3
"""ort-evaluaciones: Fetch and display ORT evaluations matching the web UI layout.

Three sections matching gestion.ort.edu.uy/evaluaciones:
  1. Para inscribirte  (CON_EVALUACIONES_ABIERTAS)
  2. Inscripto          (CON_EVALUACIONES_ARENDIR)
  3. Resultados         (CON_EVALUACIONES_RENDIDAS)
"""

import urllib.request, json, sys, os
from datetime import datetime
from collections import defaultdict

TOKEN_FILE = os.path.expanduser("~/.hermes/credentials/ort_gestion_token.txt")
API_BASE = "https://gestionapi.ort.edu.uy/ORTSecure"

HEADERS = {
    "authorization": "Basic Og==",
    "cache-control": "no-cache",
    "Content-Type": "application/x-www-form-urlencoded",
    "castmanchecontrol": "no-cache",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
}


def fmt_date(s):
    if not s or '0001' in s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace('Z', ''))
        if dt.hour == 0 and dt.minute == 0:
            return dt.strftime('%d/%m')
        return dt.strftime('%d/%m %H:%M')
    except:
        return s


def fmt_date_long(s):
    """Full date for display: dd/mm/yyyy"""
    if not s or '0001' in s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace('Z', ''))
        return dt.strftime('%d/%m/%Y')
    except:
        return s


def call_api(path):
    url = f"{API_BASE}/{path}"
    req = urllib.request.Request(url)
    for k, v in HEADERS.items():
        req.add_header(k, v)
    with open(TOKEN_FILE) as f:
        req.add_header("x-token", f.read().strip())
    resp = urllib.request.urlopen(req, timeout=15)
    body = resp.read()
    new_token = resp.headers.get('x-token')
    if new_token:
        with open(TOKEN_FILE, 'w') as f:
            f.write(new_token)
    return json.loads(body)


def get_display_date(ev, inst):
    """Get the primary display date for an evaluation instance."""
    # For obligatorios with FechaEntrega, use that
    entrega = inst.get('FechaEntrega', '')
    realizacion = inst.get('FechaRealizacion', '')
    hora = inst.get('HoraRealizacion', '')

    if entrega and '0001' not in entrega:
        return 'Entrega: ' + fmt_date(entrega), entrega

    if realizacion and '0001' not in realizacion:
        time_str = ''
        if hora and '0001' not in hora:
            try:
                ht = datetime.fromisoformat(hora.replace('Z', ''))
                if ht.hour != 0 or ht.minute != 0:
                    time_str = f" {ht.strftime('%H:%M')}"
            except:
                pass
        return (fmt_date(realizacion) or '—') + time_str, realizacion

    return '—', '9999-12-31'


def parse_items(data, estado_label):
    """Parse raw API data into uniform list of dicts."""
    items = []
    for d in data:
        materia = d['ObjMateria']['Nombre']
        for ev in d['ColEvaluaciones']:
            name = ev['Nombre']
            pmin = ev.get('PuntajeMinimo', 0)
            pmax = ev.get('PuntajeMaximo', 0)
            maxint = ev.get('MaximoIntegrantes', -100000)
            ev_type_id = ev.get('IdTipo', -1)

            for inst in ev.get('ColInstancias', []):
                display_date, sort_key = get_display_date(ev, inst)

                # Build puntaje string
                if name == 'Actuación en clase':
                    puntaje = f"{pmin}-{pmax}pts"
                elif maxint > 0:
                    puntaje = f"{pmin}-{pmax}pts ({maxint} pers)"
                else:
                    puntaje = f"{pmin}-{pmax}pts"

                # Extra info lines
                extras = []
                # Defence period
                dd = inst.get('FechaDefensaDesde', '')
                dh = inst.get('FechaDefensaHasta', '')
                if dd and '0001' not in dd:
                    dds = fmt_date_long(dd)
                    dhs = ' → ' + fmt_date_long(dh) if dh and '0001' not in dh else ''
                    extras.append(f"Defensa: {dds}{dhs}")
                # Online delivery deadline
                ho = inst.get('HoraFinEntregaOnline', '')
                if ho and '0001' not in ho:
                    extras.append(f"Entrega online hasta: {fmt_date(ho)}")
                # Result publication date
                pub = inst.get('FechaPublicacionActa', '')
                if pub and '0001' not in pub:
                    extras.append(f"Resultados: {fmt_date_long(pub)}")
                # Instance name
                iname = inst.get('Nombre', '')
                if iname and iname != 'Instancia 1':
                    extras.append(f"Instancia: {iname}")
                # Inscribible from
                fi = inst.get('FechaInscribible', '')
                if fi and '0001' not in fi:
                    extras.append(f"Inscribible desde: {fmt_date_long(fi)}")

                # Grade for RENDIDAS
                actas = inst.get('ColLineasActa', [])
                calificacion = None
                no_presento = False
                if actas:
                    c = actas[0].get('Calificacion')
                    if c is not None and c != '' and c != -100000:
                        calificacion = c
                    np = actas[0].get('NoSePresento', '')
                    no_presento = (np == 'SI')

                item = {
                    'materia': materia,
                    'nombre': name,
                    'puntaje': puntaje,
                    'fecha': display_date,
                    'sort_key': sort_key,
                    'extras': extras,
                    'estado_label': estado_label,
                    'instancia_nombre': inst.get('Nombre', ''),
                    'calificacion': calificacion,
                    'no_presento': no_presento,
                    'ev_type_id': ev_type_id,
                    'inscribible': inst.get('Inscribible', False),
                    'max_integrantes': maxint,
                    'tipo': nombre_a_tipo(name, ev_type_id),
                }
                items.append(item)
    return items


def nombre_a_tipo(name, ev_type_id):
    """Map evaluation to a display type category."""
    if name == 'Actuación en clase':
        return 'Actuación'
    if name == 'Ejercicios':
        return 'Ejercicios'
    if ev_type_id == 1:
        return 'Obligatorio'
    if ev_type_id == 2:
        return 'Parcial'
    return 'Otro'


def get_sort_key(item):
    """Sort key: date first, then type, then name."""
    return (item['sort_key'], item.get('tipo', ''), item['nombre'])


def print_table(items, section_title, emoji, show_grade=False):
    """Print a table of evaluations grouped by materia."""
    if not items:
        return

    print(f"\n  {section_title}\n")

    by_materia = defaultdict(list)
    for item in items:
        by_materia[item['materia']].append(item)

    for materia in sorted(by_materia.keys()):
        evals = sorted(by_materia[materia], key=get_sort_key)
        print(f"    📘 {materia}")

        # Headers
        if show_grade:
            print(f"      ┌─────────────────────┬────────────────┬─────────────────────────┬──────────────┐")
            print(f"      │ {'Evaluación':<19} │ {'Puntaje':<14} │ {'Fecha':<23} │ {'Nota':<12} │")
            print(f"      ├─────────────────────┼────────────────┼─────────────────────────┼──────────────┤")
            for ev in evals:
                name = f"{emoji} {ev['nombre']}"
                if ev.get('no_presento'):
                    grade_str = "Ausente"
                elif ev.get('calificacion') is not None:
                    grade_str = f"{ev['calificacion']}/{ev['puntaje'].split('-')[-1].replace('pts','')}"
                else:
                    grade_str = "Pend."
                print(f"      │ {name:<19} │ {ev['puntaje']:<14} │ {ev['fecha']:<23} │ {grade_str:<12} │")
                for ex in ev.get('extras', []):
                    print(f"         📎 {ex}")
            print(f"      └─────────────────────┴────────────────┴─────────────────────────┴──────────────┘")
        else:
            print(f"      ┌─────────────────────┬────────────────┬─────────────────────────┬──────────┐")
            print(f"      │ {'Evaluación':<19} │ {'Puntaje':<14} │ {'Fecha':<23} │ {'Estado':<8} │")
            print(f"      ├─────────────────────┼────────────────┼─────────────────────────┼──────────┤")
            for ev in evals:
                name = f"{emoji} {ev['nombre']}"
                status = "⏳ Pend."
                if section_title == "En las que estás inscripto":
                    status = "✅ Insc."
                print(f"      │ {name:<19} │ {ev['puntaje']:<14} │ {ev['fecha']:<23} │ {status:<8} │")
                for ex in ev.get('extras', []):
                    print(f"         📎 {ex}")
            print(f"      └─────────────────────┴────────────────┴─────────────────────────┴──────────┘")

        print()


def main():
    if not os.path.exists(TOKEN_FILE):
        print("❌ No hay token de gestion. Ejecutá `ort setup` primero.")
        sys.exit(1)

    try:
        abiertas = call_api("Dictados?estado=CON_EVALUACIONES_ABIERTAS&tipoEvaluacion=TODAS")
        arendir = call_api("Dictados?estado=CON_EVALUACIONES_ARENDIR&tipoEvaluacion=TODAS")
        rendidas = call_api("Dictados?estado=CON_EVALUACIONES_RENDIDAS&tipoEvaluacion=TODAS")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("   Probablemente el token expiró. Ejecutá `ort setup` para renovarlo.")
        sys.exit(1)

    insc_items = parse_items(abiertas, 'para_inscribirte')
    inscripto_items = parse_items(arendir, 'inscripto')
    rendido_items = parse_items(rendidas, 'rendidas')

    print()
    print("📋 EVALUACIONES — GESTIÓN ORT")
    print()

    # Section 1: Para inscribirte
    print("🔴 EVALUACIONES QUE TENÉS PARA INSCRIBIRTE")
    print_table(insc_items, "Para inscribirte", "📝")

    # Section 2: Inscripto
    print("🟡 EVALUACIONES EN LAS QUE ESTÁS INSCRIPTO")
    print_table(inscripto_items, "En las que estás inscripto", "📝")

    # Section 3: Resultados (only items with a grade or pending result)
    print("🟢 EVALUACIONES CON RESULTADO")
    print_table(rendido_items, "Resultados", "✅", show_grade=True)


if __name__ == '__main__':
    main()
