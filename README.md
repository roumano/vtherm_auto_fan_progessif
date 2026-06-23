# Auto Fan Progressif

Squelette initial pour un plugin externe Versatile Thermostat basé sur `vtherm_api`.

## Fichiers fournis
- `custom_components/auto_fan_progressif/manifest.json`
- `custom_components/auto_fan_progressif/__init__.py`
- `custom_components/auto_fan_progressif/const.py`
- `custom_components/auto_fan_progressif/progressive_fan.py`

## Idée
- lire `fan_modes` depuis le climate sous-jacent,
- classer les modes du plus silencieux au plus fort,
- sélectionner un mode selon l'écart de température,
- clampler l'index si le climate expose moins de modes que prévu.
