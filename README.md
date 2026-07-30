# RCD2000

Python port of RCD2000 — reinforced concrete design to BS 8110.

## Usage

```bash
python3 -m rcd2000 beam|column|slab|stair|base|continuous-beam|info
```

## Modules

| Command | Design |
|---------|--------|
| `beam` | Simply supported & continuous beams |
| `column` | Axial, uniaxial & biaxial columns |
| `slab` | One-way, two-way & cantilever slabs |
| `stair` | Straight-flight stairs |
| `base` | Isolated & combined footings |
| `continuous-beam` | Clapeyron analysis |

## Reference

Original FORTRAN source by V.O. Oyenuga (1999) is in `references/`.
