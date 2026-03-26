# Juego Animales que explotan

## Instalacion

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Build de Windows en GitHub

El ejecutable de Windows se genera con el workflow [build-windows.yml](/Users/antonioemilioarmadacastillo/Documents/Invoa/Juegos/Animales-explotan/.github/workflows/build-windows.yml).

El build usa [img/icono-ventana.ico](/Users/antonioemilioarmadacastillo/Documents/Invoa/Juegos/Animales-explotan/img/icono-ventana.ico) como icono del archivo `AnimalesExplotan.exe`.

Para obtenerlo:

1. Sube el repositorio a GitHub.
2. En GitHub, entra a la pestaña `Actions`.
3. Abre el workflow `Build Windows`.
4. Ejecuta `Run workflow` para lanzarlo manualmente.
5. Cuando termine, abre la corrida y descarga el artifact `AnimalesExplotan-windows`.

Tambien puedes dispararlo creando y subiendo un tag que empiece con `v`, por ejemplo:

```bash
git tag v1.0.0
git push origin v1.0.0
```

El artifact descargado contiene la carpeta `AnimalesExplotan` con:

- `AnimalesExplotan.exe`
- `config.yaml`
- los archivos necesarios del juego (`img`, `snd`, librerias y runtime)

Conviene distribuir esa carpeta completa, no solo el `.exe`.

## Iconos

El proyecto usa dos archivos de icono:

- [img/icono-ventana.png](/Users/antonioemilioarmadacastillo/Documents/Invoa/Juegos/Animales-explotan/img/icono-ventana.png): icono de la ventana del juego en `pygame`
- [img/icono-ventana.ico](/Users/antonioemilioarmadacastillo/Documents/Invoa/Juegos/Animales-explotan/img/icono-ventana.ico): icono del ejecutable de Windows generado con PyInstaller

Si cambias el PNG, puedes regenerar el `.ico` con:

```bash
.venv/bin/python -c "from PIL import Image; img = Image.open('img/icono-ventana.png').convert('RGBA'); img.save('img/icono-ventana.ico', format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"
```

Despues de eso, vuelve a ejecutar el workflow `Build Windows` en GitHub Actions o crea un tag nuevo con prefijo `v` para generar un artifact actualizado.

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

En builds empaquetados, el juego primero busca un `config.yaml` externo al lado del ejecutable. Si no existe, usa el `config.yaml` incluido dentro del bundle como fallback.

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
