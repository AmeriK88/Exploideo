# CSS Architecture

Este directorio contiene el nuevo sistema de estilos organizado según ITCSS + BEM.

## Capas

1. **settings/**: variables y tokens CSS globales. No usar en HTML.
2. **tools/**: mixins o funciones compartidas (actualmente vacío).
3. **generic/**: reset y base global de `html`, `body`.
4. **elements/**: estilos para etiquetas semánticas y `c-article`.
5. **objects/**: patrones de layout reutilizables (`o-stack`, `o-grid`, `o-cta-actions`).
6. **components/**: bloques independientes (`c-button`, `c-card`, etc.).
   - `components/home/` contiene los componentes específicos de la landing.
7. **utilities/**: clases prefijadas `u-` para usos de alto nivel.

## Convenciones

- Prefijos: `c-` componente, `o-` objeto, `u-` utilidad.
- Modificadores: BEM `--estado` (por ejemplo `c-button--primary`).
- Las clases no deben depender de la estructura del DOM ni usar selectores globales.
- Las landing se aíslan usando `body.landing` o componentes dentro de `components/home`.

## Migración
Ver `project_structure.md` o el plan dentro de la documentación original para pasos de migración incremental.
