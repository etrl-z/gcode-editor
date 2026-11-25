# G-code Layer Editor

Un editor G-code per la navigazione tra livelli di stampa con PyQt6.

## Funzionalità
- Elenco dei livelli con altezza Z.
- Navigazione tramite lista (Shift per multi-selezione).
- Commenta selezione.
- Salva / Ripristina.
- Undo/Redo tramite Qt.
- Syntax highlighting (commenti verdi, X rosso, Y giallo, Z blu).

## Esecuzione
```bash
source venv/bin/activate
python gui.py "AI3M_Articulated mouse (adjusted tail).gcode"
```
