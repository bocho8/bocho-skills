# Gestion API Endpoints

Discovered by reverse-engineering the AngularJS source code of gestion.ort.edu.uy.

## Auth Mechanism

**Not cookies.** Gestion uses JWT tokens stored in `sessionStorage`.

### Headers required for ALL API calls

Missing any header → error code 15 ("token inválido"):

```
x-token: <jwt from sessionStorage.token>
authorization: Basic Og==
cache-control: no-cache
Content-Type: application/x-www-form-urlencoded
castmanchecontrol: no-cache
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
```

### Token refresh

The response includes a **new `x-token` header** on every successful request. Always save it:

```python
new_token = resp.headers.get('x-token')
if new_token:
    # save for next call
```

### Error codes

| Message | Meaning |
|---|---|
| `"15"` | Token inválido/expirado. El usuario necesita loguearse de nuevo y copiar `sessionStorage.token` fresco. |
| `"13"` | Otro error de validación. |
| Empty body (HTTP 200) | Token expirado o endpoint requiere parámetros adicionales. |

## API Base URL

```
https://gestionapi.ort.edu.uy/ORTSecure/
```

Discovered via `<meta name="api-ort-secure-url" content="...">` in the Angular app's HTML.

Also available (non-secure API, used for login):
```
https://gestionapi.ort.edu.uy/ORT/
```

## Endpoints by category

### General

| Endpoint | Method | Description |
|---|---|---|
| `General/FechaHora` | GET | Server date/time. Returns string `"2026-06-28T16:40:44"` |
| `General/ContactoBedelias` | GET | Bedelías contact list. Returns `[{IdBedeliaDepartamento, Nombre}]` |
| `General/Versiones` | GET | Version info. Returns `{VersionSistema, VersionFrontEnd, VersionBackEnd}` |
| `General/Paises` | GET | Countries list |
| `General/Universidades?CodigoPais=N` | GET | Universities by country |
| `General/Loguear` | POST | Server-side logging |
| `General/FrontLog` | POST | Frontend logging (secure) |
| `Login/FrontLog` | POST | Frontend logging (non-secure) |

### Evaluaciones / Exams

| Endpoint | Method | Description |
|---|---|---|
| `Dictados?estado=CON_EVALUACIONES_ABIERTAS&tipoEvaluacion=TODAS` | GET | Evaluations open for registration (you're not yet inscribed). 3-section web UI tab 1. |
| `Dictados?estado=CON_EVALUACIONES_ARENDIR&tipoEvaluacion=TODAS` | GET | Evaluations you're already registered for. 3-section web UI tab 2. |
| `Dictados?estado=CON_EVALUACIONES_RENDIDAS&tipoEvaluacion=TODAS` | GET | Evaluations with results. Grades/stats in `ColInstancias[].ColLineasActa[].Calificacion`. 3-section web UI tab 3. |
| `Examenes?estado=CON_EVALUACIONES_ARENDIR` | GET | Final exams pending |
| `Examenes?estado=CON_EVALUACIONES_RENDIDAS` | GET | Final exams already taken |
| `Dictados/{idDictado}/Evaluaciones` | GET | Evaluations for a specific dictado (course section) |
| `Dictados/{idDictado}/Evaluaciones/{idEval}/Ticket` | GET | Ticket/confirmation for an evaluation |
| `Dictados/0/Evaluaciones/{idEval}/Inscripcion` | POST | Register for an evaluation |
| `Examenes/{idExamen}/Insripciones` | GET | Exam registrations |
| `Examenes/{idExamen}/Ticket` | GET | Exam ticket |

### Dictado response structure

```json
{
  "Id": 75865,
  "ObjMateria": { "IdMateria": 1479, "Nombre": "Programación 1", "Descripcion": "Programación 1" },
  "MinimoAprobacion": 70,
  "MinimoExoneracion": -100000,
  "ColEvaluaciones": [
    {
      "Id": 169993,
      "Nombre": "Parcial 2",
      "PuntajeMinimo": 20,
      "PuntajeMaximo": 40,
      "MaximoIntegrantes": -100000,
      "InscripcionObligatoria": "SI",
      "EsParcialReal": "SI",
      "EntregaDigital": "NO",
      "ColInstancias": [
        {
          "Id": 186827,
          "Nombre": "Instancia 1",
          "Observaciones": "",
          "FechaRealizacion": "2026-07-07T00:00:00",
          "HoraRealizacion": "2026-06-28T09:00:00",
          "FechaPublicacionActa": "2026-07-20T00:00:00",
          "FechaEntrega": "0001-01-01T00:00:00",
          "FechaCierreActa": "0001-01-01T00:00:00",
          "Inscribible": true,
          "FechaInscribible": "0001-01-01T00:00:00",
          "ClaveInscipcion": "7000420b893736520"
        }
      ]
    }
  ]
}
```

Date fields with `0001-01-01` = null/unset. Key date field is `FechaRealizacion` (actual exam date).

### Additional fields for Obligatorio-type evaluations

Obligatorios (IdTipo=1) have extra date fields vs Parciales (IdTipo=2):

| Field | Description | Example |
|---|---|---|
| `FechaEntrega` | Submission deadline | `"2026-06-29T00:00:00"` |
| `FechaDefensaDesde` | Defense/registration period start | `"2026-06-29T00:00:00"` |
| `FechaDefensaHasta` | Defense/registration period end | `"2026-07-20T00:00:00"` |
| `HoraFinEntregaOnline` | Online submission cut-off time | `"2026-06-28T21:00:00"` |
| `MaximoIntegrantes` | Max team members (N>0) | `2` |
| `Inscribible` | Whether registration is open | `true` |
| `ClaveInscipcion` | Registration key | `"7000420b893736520"` |

**Date formatting tip**: `HoraRealizacion` stores a full datetime, not just time. When it's midnight (`T00:00:00`), it means no meaningful time is set — don't display it. Only show the time component when hour+minute != 0.

### Perfil / Profile

| Endpoint | Method | Description |
|---|---|---|
| `PerfilPersonal?estado=VALIDACIONES` | GET | Profile validations (password expiry, surveys pending, etc.) |
| `PerfilPersonal/Agenda` | GET | Personal calendar/agenda |
| `PerfilPersonal/RecibeResultados?recibeResultado=BOOL` | POST | Toggle email results preference |
| `PerfilPersonal/RecibeNotificacionApp` | GET/POST | App notification preferences |
| `PerfilPersonal/CambiarPassword` | PUT | Change password |

### Perfil Académico

| Endpoint | Method | Description |
|---|---|---|
| `PerfilAcademico/Titulos?estado=TODOS` | GET | Academic titles |
| `PerfilAcademico/Productos?estado=TODOS` | GET | Academic products |
| `PerfilAcademico/CreditosACD` | GET | ACD credits |
| `PerfilAcademico/MateriaDelTitulo?idTitulo=N` | GET | Subjects for a title |
| `PerfilAcademico/MateriaDelTitulo/PreviasDeMateria?idMateria=N&idTitulo=N` | GET | Prerequisites |

### Inscripciones / Enrolment

| Endpoint | Method | Description |
|---|---|---|
| `Cursos/Inscripciones` | GET | Enrolments |
| `Cursos/Inscripciones?estado=TRAMITE_DE_MODIFICACION` | GET | Enrolment modification requests |
| `Cursos/Productos?altaInscripcion=true` | GET | Available products for enrolment |
| `Cursos/OfertasPorProducto?idProducto=N&idComienzo=N` | GET | Course offerings |
| `Cursos/Inscripciones/TramiteSolicitud` | POST | Submit enrolment request |

### Login / Auth (non-secure API)

| Endpoint | Method | Description |
|---|---|---|
| `Login` | POST | Authenticate: `{Usuario, Password, Response}` (reCAPTCHA token) |
| `Login/MostrarCaptcha?usuario=EMAIL` | GET | Check if CAPTCHA is needed |
| `Login/TipoDeAcceso` | GET | Check access type for user |
| `Login/Activar2FA-TOTP` | POST | Activate TOTP 2FA |
| `Login/Verificar2FA-TOTP` | POST | Verify TOTP code during login |
| `General/Estado2FA-TOTP` | GET | Get 2FA status |
| `General/Crear2FA-TOTP` | POST | Create TOTP secret |
| `General/Sustituir2FA-TOTP` | GET/POST | Replace 2FA device |

### Certificates / Constancias

| Endpoint | Method | Description |
|---|---|---|
| `Certificado/CAlumnoActivo?idProducto=N&enviaMail=BOOL` | GET | Active student certificate |
| `Certificado/CGraduado?idTitulo=N&enviaMail=BOOL` | GET | Graduate certificate |
| `Certificado/CInscripcionEvaluacion?idInstancia=N&enviaMail=BOOL` | GET | Exam registration certificate |
| `Certificado/CPresentacionEvaluacion?idInstancia=N&enviaMail=BOOL` | GET | Exam presentation certificate |

### Payments

| Endpoint | Method | Description |
|---|---|---|
| `Pagos/CtaCte?estado=...` | GET | Account statement |
| `Pagos/Bancos` | GET | Available banks |
| `Pagos/Carritos` | GET/POST | Shopping cart |
| `Pagos/Carritos/Pagar` | POST | Pay |
| `Pagos/Carritos/UrlCrearFactura?tipoPago=...` | GET | Invoice URL |

### Entrega Digital

| Endpoint | Method | Description |
|---|---|---|
| `EntregaDigital/CrearEquipo` | POST | Create team |
| `EntregaDigital/{id}/Equipo` | GET | Get team info |
| `EntregaDigital/{id}/ValidarIntegrante?idIntegrante=N` | GET | Validate team member |

## sessionStorage fields set at login

These are populated from the login response, not fetched via API. User can provide them for context:

| Key | Description | Example |
|---|---|---|
| `token` | JWT for API auth | `eyJhbG...` |
| `DatosPersona` | Full JSON with personal data | `{"CodigoPersona":123456,"PrimerNombre":"Nombre","PrimerApellido":"Apellido",...}` |
| `DataCodigoPersona` | Student ID | `"123456"` |
| `DataMailPersona` | Email | `"estudiante@ejemplo.com"` |
| `DataPrimerNombre` | First name | `"Nombre"` |
| `DataPrimerApellido` | Last name | `"Apellido"` |
| `Variables` | App session state JSON | `{"Origen":"vPrincipal","Redireccion":null,...}` |

## App `State` values (Angular UI router states)

Each maps to a section in the app. Some may have dedicated API endpoints:

- `inicio` — Dashboard
- `datospersona` — Personal data
- `inscripciones` — Enrolments
- `cursosactivos` — Active courses
- `creditosacademicos` — Academic credits
- `evaluaciones` — Evaluations (Dictados endpoint)
- `examenes` — Exams (Examenes endpoint)
- `escolaridad` — Academic history
- `encuestas` — Surveys
- `pagos` — Payments
- `tramites` — Procedures
- `previas` — Prerequisites
- `laboratorio` — Labs
- `certificados` — Certificates
- `notificaciones` — Notifications
