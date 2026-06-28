---
name: ort-access
description: Access ORT Uruguay student sites (gestion.ort.edu.uy and aulas.ort.edu.uy) that require 2FA authentication. Use this skill whenever the user mentions ORT, gestion, aulas, wants to check classes, assignments, grades, course materials, evaluations, exams, calendars, or any ort.edu.uy site. The skill handles auth flow (cookies export for aulas, JWT token for gestion), expiry detection, API calls, and navigation. Always trigger on any ORT-related request — even casual queries like "check my courses", "what's due this week", "when are my exams", "ver fechas de parciales", or "listar evaluaciones". If the user is a student at ORT Uruguay and asks about anything academic, this skill applies.
---

# ort-access

Skill for accessing ORT Uruguay's student portals. Both sites require 2FA via authenticator app — the skill delegates authentication to the user.

## Sites

| Site | Type | Auth | Storage | Expiry |
|---|---|---|---|---|
| **aulas.ort.edu.uy** | Moodle | cookies.txt extension | `~/.hermes/credentials/ort_aulas_cookies.txt` (Netscape format) | ~hours |
| **gestion.ort.edu.uy** | Angular SPA | `sessionStorage.token` (JWT) via x-token header | `~/.hermes/credentials/ort_gestion_token.txt` (raw JWT) | ~30 min |

## Why this approach

- **aulas**: Uses cookies (`MoodleSession` with HttpOnly+Secure flags). `browser_*` tools can't access the user's session. `computer_use` is unreliable on KDE/Wayland. **curl + cookies.txt** is the simplest reliable method.
- **gestion**: An AngularJS SPA. No cookies — uses JWT from `sessionStorage` sent as `x-token` header (not Bearer) with `authorization: Basic Og==`. Token expires in ~30 minutes. User copies `sessionStorage.token` from DevTools console.

**Browser-agnostic**: The skill works with any browser. For aulas, use the cookies.txt extension. For gestion, use DevTools console.

## Tools required

- `terminal` — run curl, read/write credential files
- `read_file` / `write_file` / `patch` — manage credential files

## Credential files

```
~/.hermes/credentials/
  ort_aulas_cookies.txt     — Netscape format, from cookies.txt extension
  ort_gestion_token.txt     — raw JWT string from sessionStorage.token
```

## Commands

### `ort setup` — First-time or refresh setup for both sites

#### aulas setup
1. Tell the user:
   - "Andá a aulas.ort.edu.uy en tu navegador y asegurate de estar logueado (con 2FA)"
   - "Abrí la extensión cookies.txt — clickeá el ícono → apretá **Copy** en 'Current site'"
   - "Pegá todo el texto acá"
2. Save to `ort_aulas_cookies.txt`
3. Verify: file has at least one tab-separated cookie line (not just headers)

#### gestion setup
1. Tell the user:
   - "Andá a gestion.ort.edu.uy en tu navegador, logueate (con 2FA)"
   - "Abrí DevTools (F12) → Console"
   - "Escribí `sessionStorage.token` y Enter"
   - "Copiá el string (sin las comillas) y pegalo acá"
2. Save to `ort_gestion_token.txt`
3. Verify: starts with `eyJ` (standard JWT prefix)

### `ort navigate aulas <url>` — Fetch an aulas page

Shortcuts:
- `ort navegar aulas` → `https://aulas.ort.edu.uy/my/` (dashboard)
- `ort navegar aulas cursos` → course list check

Steps:
1. Read cookie file. Missing → ask to run `ort setup`
2. `curl -s --cookie ~/.hermes/credentials/ort_aulas_cookies.txt -L "<url>"`
3. Detect expired session: Moodle always has a login link in the footer, so checking for `/login/` gives false positives. Instead check:
   - The HTML contains a **login form** (search for `<input` with `name="username"` or `id="username"` or a password field)
   - The page redirects to a URL containing `/login/index.php` (check the final URL after curl -L)
   - There is NO user name or logout link in the page (search for "Cerrar sesión" or "logout")
4. If expired: ask user to re-export cookies via the cookies.txt extension (open popup → Copy on Current site), save, retry
5. If OK: extract meaningful content (headings, course names, assignments, dates)

### `ort evaluaciones` — Mostrar todas las evaluaciones

Fetches all evaluation data from gestion and displays it in 3 sections matching the web UI:

1. **🔴 Evaluaciones que tenés para inscribirte** (CON_EVALUACIONES_ABIERTAS)
2. **🟡 Evaluaciones en las que estás inscripto** (CON_EVALUACIONES_ARENDIR)
3. **🟢 Evaluaciones con resultado** (CON_EVALUACIONES_RENDIDAS)

**Steps:**

1. Read token file. Missing → ask to run `ort setup`
2. Call these 3 API endpoints with ALL required headers:
   - `Dictados?estado=CON_EVALUACIONES_ABIERTAS&tipoEvaluacion=TODAS` — para inscribirte
   - `Dictados?estado=CON_EVALUACIONES_ARENDIR&tipoEvaluacion=TODAS` — inscripto
   - `Dictados?estado=CON_EVALUACIONES_RENDIDAS&tipoEvaluacion=TODAS` — resultados
3. For each response, parse: `Dictado[] → ColEvaluaciones[] → ColInstancias[]`
   - Grades are in `inst.ColLineasActa[0].Calificacion`
   - `inst.ColLineasActa[0].NoSePresento` = `"SI"` if absent
4. Display output with actual grades where available:

   **🔴 Para inscribirte** — shows inscribible dates, defense periods, instance names
   **🟡 Inscripto** — shows when you're already registered
   **🟢 Resultados** — shows grades like `8/10`, `14/15`, or `Ausente` / `Pend.`

5. Save the refreshed `x-token` from the response headers after each API call.

**Implementation**: Bundled script at `scripts/ort_evaluaciones.py`. Run it with `python3 ~/.hermes/skills/ort-access/scripts/ort_evaluaciones.py`.

**Expiry note**: If the token expired, the script will fail with a connection error. Run `ort setup` to provide a fresh token from `sessionStorage.token` in DevTools.

### `ort navigate gestion <path>` — Call a gestion API endpoint

Shortcuts:
- `ort navegar gestion` → list available API info
- `ort navegar gestion evaluaciones` → fetch Evaluaciones data
- `ort navegar gestion agenda` → fetch calendar/agenda

Steps:
1. Read token file. Missing → ask to run `ort setup`
2. Call the API with ALL required headers (missing any will give error code 15):
   ```bash
   curl -s -H "x-token: $(cat ~/.hermes/credentials/ort_gestion_token.txt)" \
     -H "authorization: Basic *** \
     -H "cache-control: no-cache" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "castmanchecontrol: no-cache" \
     -H "X-Content-Type-Options: nosniff" \
     -H "X-XSS-Protection: 1; mode=block" \
     "https://gestionapi.ort.edu.uy/ORTSecure/<path>"
   ```
   The response includes a **new `x-token` header** — save it to refresh the session.
3. Detect expired: HTTP 400 or empty body → ask user for fresh `sessionStorage.token`
4. If OK: parse JSON response and present to user

### `ort status` — Check credentials

Report existence, size, and last modified time of both credential files.

## Reference files

- `references/gestion-api-endpoints.md` — full list of discovered gestion API endpoints, auth mechanism, sessionStorage fields, and error handling. Read this when working with the gestion API.

## Known API endpoints (gestion)

Full reference: see `references/gestion-api-endpoints.md` for the complete list of endpoints discovered from the AngularJS source code, including login, profile, academic, 2FA, and document endpoints.

| Endpoint | Description |
|---|---|
| `General/ContactoBedelias` | Bedelías contact list |
| `General/FechaHora` | Server date/time |
| `PerfilPersonal/Agenda` | Personal agenda |
| `PerfilPersonal?estado=VALIDACIONES` | Profile validations |
| `General/Versiones` | Version info |
| `Dictados?estado=CON_EVALUACIONES_ABIERTAS&tipoEvaluacion=TODAS` | Evaluaciones abiertas para inscribirte (no inscripto aún) |
| `Dictados?estado=CON_EVALUACIONES_ARENDIR&tipoEvaluacion=TODAS` | Evaluaciones en las que estás inscripto |
| `Dictados?estado=CON_EVALUACIONES_RENDIDAS&tipoEvaluacion=TODAS` | Evaluaciones con resultado (incluye notas en `ColInstancias[].ColLineasActa[].Calificacion`) |
| `Examenes?estado=CON_EVALUACIONES_ARENDIR` | Exámenes pendientes |
| `PerfilAcademico/Titulos?estado=TODOS` | Academic titles |
| `PerfilAcademico/Productos?estado=TODOS` | Academic products |

**Note:** The Angular app's menu `State` values (inicio, inscripciones, cursosactivos, evaluaciones, examenes, escolaridad, etc.) each likely map to an API endpoint. If you need a specific section, check the JS source for its API path — try appending the State name to the secure API base URL with GET first.

The Angular app reads several values from `sessionStorage` at login time (not fetched via API):
- `DatosPersona` — full JSON: codigo, name, email, etc.
- `DataCodigoPersona`, `DataMailPersona`, `DataPrimerNombre`, `DataPrimerApellido`
- `Variables` — app state (view, redirect, tramites, certificados)

User can provide these too if needed for context.

## Extracting course info from aulas

Moodle loads course lists dynamically via JavaScript. The dashboard page (`/my/`) shows courses but the HTML may not contain direct links. Approaches:

1. **Calendar view**: `https://aulas.ort.edu.uy/calendar/view.php?view=upcoming` — upcoming events with dates
2. **Course index**: `https://aulas.ort.edu.uy/course/index.php?categoryid=N` — lists courses in a category
3. **Grade report**: `https://aulas.ort.edu.uy/grade/report/user/index.php?id=N` — grades for a specific course
4. **Assignments**: `https://aulas.ort.edu.uy/mod/assign/index.php?id=N` — assignments for a course

Use `ort navigate aulas <url>` to fetch and parse these.

## Expiry detection

- **aulas**: Session cookie expires after hours. HTML contains login redirect or login form. Ask user to re-export cookies via the cookies.txt extension (open popup → Copy on Current site).
- **gestion**: JWT expires after ~30 minutes. API returns 400 or empty body. Ask user to re-copy `sessionStorage.token` from DevTools.

## Pitfalls

- **Empty aulas cookie export**: User may not be logged in. Ask them to login with 2FA first.
- **cookies.txt extension**: Must be installed from Firefox Add-ons or Chrome Web Store (https://github.com/hrdl-github/cookies-txt). Open the extension popup → press **Copy** on "Current site". Works with any browser that supports the extension.
- **Gestion token expiry**: Very short (~30 min). The token field may be in `DatosPersona.Password` or the top-level `token` value.
- **Gestion token refresh is mandatory**: Every API response includes a new `x-token` header. You MUST save it before the next call — the old token becomes invalid once a new one is issued. The Angular app does this automatically via its response interceptor; your code must do it explicitly.
- **Gestion 400 errors**: All endpoints return 400 when the token is expired. No distinction between "bad request" and "expired". Always try a fresh token before debugging endpoints.
- **Moodle dynamic content**: Course lists and calendar events are loaded via JS templates. Direct HTML parsing may not find them. Use the dedicated pages (`/calendar/view.php`, `/grade/report/user/index.php`, etc.).
