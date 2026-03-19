# Juego Animales que explotan

## Instalacion

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Configuracion

El juego lee [config.yaml](/Users/antonioemilioarmadacastillo/Documents/Invoa/Juegos/Animales-explotan/config.yaml) al iniciar. Ahi podés cambiar opciones como:

- `fullscreen`
- `window_width`
- `window_height`
- `show_cursor`
- `fps`
- `music_volume`
- `hover_explode_delay_seconds`
- `time_out_seconds`
- `session_target_count`
- `cursor_trace_hz`
- `data_output_dir`
- `show_session_progress`

## Telemetria

Antes de empezar una sesion el juego pide un `session_id`. Al terminar, exporta datos en la carpeta configurada por `data_output_dir`.

- `session_summary.csv`: resumen por sesion
- `target_metrics.csv`: metricas por objetivo
- `cursor_trace.jsonl`: trayectoria cruda del cursor
- `events.jsonl`: eventos discretos de la sesion

## Cierre de sesion

Al finalizar la sesion el juego muestra una pantalla de resultados con indicadores principales y secundarios y exporta automaticamente un `reporte_sesion.pdf`.

- primera hoja con indicadores resumidos y grafico de trayectorias
- hojas siguientes con metricas por objetivo
