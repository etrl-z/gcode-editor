#!/bin/bash
# Script di avvio per G-code Layer Editor
# Assicura che l'ambiente virtuale sia caricato correttamente

DIRECTORY="/home/emilio/Documenti/repos/gcode-editor"
cd "$DIRECTORY" || exit 1

# Attiva l'ambiente virtuale
source venv/bin/activate

# Esegue l'editor passando il file ricevuto come argomento
# "$1" è il percorso del file passato dal tasto destro del mouse
python3 gui.py "$1"
