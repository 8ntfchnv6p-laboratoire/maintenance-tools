# CLAUDE.md

Guidance for AI assistants (Claude Code and others) working in this repository.

## What this repository is

`maintenance-tools` is a small toolkit for **industrial maintenance field
diagnostics** (French: *diagnostic terrain, maintenance industrielle*). The
intended users are field electromechanics/technicians who use Claude to
troubleshoot machines — PLCs, variable-frequency drives (VFDs/*variateurs*),
safety relays, and industrial fieldbus networks — on the shop floor.

The domain is French-first: the machines referenced are woodworking lines
(HOMAG, Holzma, Biesse, SCM), the drives are KEB / Lenze / IndraDrive, and all
user-facing text is in **French (fr-CA)**. Preserve that language and vocabulary
in any user-facing content you add or edit.

## Repository layout

The repository is intentionally tiny and flat — there is no build system, no
dependencies, and no package manager.

```
.
├── README.md                  # One-line stub title only
└── diagnostic-template.html   # The actual tool (self-contained, ~650 lines)
```

### `diagnostic-template.html`

A **single self-contained HTML page** — no external JS/CSS bundles, no build
step. Open it directly in a browser (`file://`) and it works. It is a
**structured prompt builder**: the technician fills in a form describing a
machine fault, and the page assembles a well-formed Markdown diagnostic prompt
to paste into Claude.

Structure of the file (all inline):
- **`<style>` block** — a dark "terminal/instrument" theme driven by CSS custom
  properties in `:root` (`--bg`, `--surface`, `--accent: #f59e0b` amber, mono
  font JetBrains Mono, sans IBM Plex Sans). Fonts load from Google Fonts via
  `@import`.
- **Form sections** — numbered `①`–`⑦`, each a `.section` card:
  1. Identification (machine, section, axe/organe, variateur/PLC, mode contrôle)
  2. Symptôme (+ fréquence, depuis quand)
  3. Codes erreur
  4. Contexte
  5. Déjà vérifié (marked *critique* — the more filled, the less Claude re-asks)
  6. Optional toggle sections: **Réseau bus**, **Après intervention**,
     **Photos / Captures**
  7. Ce que j'attends (default: top-3 ranked causes, measurement points, I/O &
     diagnostic bits, correction procedure)
- **`<script>` block** — plain vanilla JS, no framework. Key functions:
  - `buildPrompt()` — reads every field by `id` and concatenates a Markdown
    prompt string. **This is the heart of the tool.**
  - `copyPrompt()` — copies the built prompt to the clipboard (with a
    `document.execCommand('copy')` fallback for non-secure contexts).
  - `saveLocal()` / `loadLocal()` — persist a draft to `localStorage` under the
    key `diag-draft`.
  - `clearAll()` / `toggleVariant()` — reset and show/hide optional sections.

A **LOTO safety banner** (🔒 *Consignation · Vérification absence d'énergie ·
Cadenas personnel*) sits at the top of the page. This reflects a domain-wide
safety convention: never remove or downplay lock-out/tag-out reminders.

## Key conventions

- **Zero build, zero dependencies.** Everything ships in one HTML file. Do not
  introduce a bundler, framework, `package.json`, or npm dependency unless
  explicitly asked — it would break the "open the file and it works" model.
- **Keep it self-contained.** New behavior goes in the existing inline
  `<style>` / `<script>` blocks. The only accepted external resource is Google
  Fonts.
- **Field ↔ builder contract.** Each form control has a stable `id`. If you add
  a field, you must (a) give it an `id`, (b) read it in `buildPrompt()`, and
  (c) add that `id` to the `getFormData()` array so save/load draft keeps
  working. These three places must stay in sync.
- **French, fr-CA.** All labels, placeholders, buttons, and generated prompt
  text are French. Dates use `toLocaleDateString('fr-CA')`. Match this.
- **Theme via CSS variables.** Reuse the `:root` custom properties for colors
  rather than hard-coding hex values, so the instrument look stays consistent.
- **Safety first.** Preserve the LOTO banner and any safety framing in
  generated prompts.

## Development workflow

- **Run / preview:** open `diagnostic-template.html` in any browser. No server
  needed. To verify JS changes, use the browser devtools console.
- **Testing:** there is no automated test suite. Verify manually: fill fields →
  *Copier le prompt* → confirm the assembled Markdown is well-formed; toggle the
  optional sections; save then reload a draft to confirm `localStorage`
  round-trips.
- **No CI / linters** are configured. Keep the HTML valid and the JS
  framework-free.

## Git & branch conventions

- Default branch: `main`.
- Do work on a feature branch, commit with clear descriptive messages, and push
  with `git push -u origin <branch>`.
- Do **not** open a pull request unless explicitly asked.

## Related Claude skills

This environment ships domain skills that pair with this tool — e.g. field
diagnostic skills for Allen-Bradley Guardmaster safety relays (MSR138DP,
MSR210P, GSR 440R), fieldbus troubleshooting (Profinet/Profibus/Modbus/
EtherNet-IP, EtherCAT/CANopen/IO-Link), CODESYS/TwinCAT Structured Text, KUKA
KRL, HOMAG placage lines, and electrical schematic reading. The
`diagnostic-template.html` prompt structure (identification → symptôme → codes →
contexte → déjà vérifié → attente) mirrors what those skills expect as input.
When helping a user with a field fault, prefer invoking the relevant skill and
gather the same fields this template collects.
