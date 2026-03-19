import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median


SESSION_SUMMARY_FIELDS = [
    "id_sesion",
    "iniciada_en",
    "finalizada_en",
    "estado",
    "cantidad_objetivos_configurada",
    "cantidad_objetivos_completada",
    "tasa_completitud",
    "duracion_sesion_ms",
    "distancia_total_cursor_px",
    "promedio_tiempo_adquisicion_objetivo_ms",
    "mediana_tiempo_adquisicion_objetivo_ms",
    "promedio_eficiencia_trayectoria",
    "promedio_reingresos_hover",
    "promedio_tiempo_hover_hasta_explosion_ms",
]

TARGET_METRIC_FIELDS = [
    "id_sesion",
    "indice_objetivo",
    "id_animal",
    "tiempo_aparicion_ms",
    "posicion_objetivo_x",
    "posicion_objetivo_y",
    "cursor_x_al_aparecer",
    "cursor_y_al_aparecer",
    "tiempo_explosion_ms",
    "tiempo_adquisicion_ms",
    "longitud_total_trayectoria_px",
    "distancia_linea_recta_px",
    "eficiencia_trayectoria",
    "cantidad_ingresos_hover",
    "tiempo_hover_hasta_explosion_ms",
    "cantidad_muestras_traza",
]

ESTADOS_EXPORTADOS = {
    "completed": "completada",
    "aborted": "abortada",
}

EVENTOS_EXPORTADOS = {
    "session_started": "sesion_iniciada",
    "target_spawned": "objetivo_aparecido",
    "hover_started": "hover_iniciado",
    "hover_broken": "hover_interrumpido",
    "target_exploded": "objetivo_explotado",
    "target_timed_out": "objetivo_expirado",
    "session_finished": "sesion_finalizada",
}


def _distance(point_a, point_b):
    return math.hypot(point_b[0] - point_a[0], point_b[1] - point_a[1])


def _mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def _round_float(value):
    return round(float(value), 3)


@dataclass
class TargetTelemetry:
    session_id: str
    target_index: int
    animal_id: str
    spawn_ts_ms: int
    spawn_x: int
    spawn_y: int
    cursor_x_at_spawn: int
    cursor_y_at_spawn: int
    target_center_x: float
    target_center_y: float
    explode_ts_ms: int | None = None
    acquisition_time_ms: int | None = None
    total_path_length_px: float = 0.0
    straight_line_distance_px: float = 0.0
    path_efficiency: float = 0.0
    hover_entry_count: int = 0
    hover_time_until_explode_ms: int = 0
    trace_sample_count: int = 0
    last_trace_position: tuple[int, int] | None = None
    is_hovering: bool = False
    hover_started_at_ms: int | None = None

    def __post_init__(self):
        self.straight_line_distance_px = _distance(
            (self.cursor_x_at_spawn, self.cursor_y_at_spawn),
            (self.target_center_x, self.target_center_y),
        )

    def add_sample(self, cursor_position):
        if self.last_trace_position is not None:
            self.total_path_length_px += _distance(self.last_trace_position, cursor_position)
        self.last_trace_position = cursor_position
        self.trace_sample_count += 1

    def update_hover(self, on_target, now_ms):
        if on_target and not self.is_hovering:
            self.is_hovering = True
            self.hover_started_at_ms = now_ms
            self.hover_entry_count += 1
            return "hover_started"

        if not on_target and self.is_hovering:
            self._commit_hover_time(now_ms)
            return "hover_broken"

        return None

    def current_hover_elapsed_ms(self, now_ms):
        if not self.is_hovering or self.hover_started_at_ms is None:
            return 0
        return max(0, now_ms - self.hover_started_at_ms)

    def finalize_explosion(self, now_ms):
        if self.is_hovering:
            self._commit_hover_time(now_ms)
        self.explode_ts_ms = now_ms
        self.acquisition_time_ms = now_ms - self.spawn_ts_ms
        self.path_efficiency = self._calculate_path_efficiency()

    def finalize_incomplete(self, now_ms):
        if self.is_hovering:
            self._commit_hover_time(now_ms)
        self.path_efficiency = self._calculate_path_efficiency()

    def _commit_hover_time(self, now_ms):
        if self.hover_started_at_ms is not None:
            self.hover_time_until_explode_ms += max(0, now_ms - self.hover_started_at_ms)
        self.is_hovering = False
        self.hover_started_at_ms = None

    def _calculate_path_efficiency(self):
        if self.total_path_length_px == 0:
            return 1.0 if self.straight_line_distance_px == 0 else 0.0

        efficiency = self.straight_line_distance_px / self.total_path_length_px
        return max(0.0, min(1.0, efficiency))

    def to_row(self):
        return {
            "id_sesion": self.session_id,
            "indice_objetivo": self.target_index,
            "id_animal": self.animal_id,
            "tiempo_aparicion_ms": self.spawn_ts_ms,
            "posicion_objetivo_x": self.spawn_x,
            "posicion_objetivo_y": self.spawn_y,
            "cursor_x_al_aparecer": self.cursor_x_at_spawn,
            "cursor_y_al_aparecer": self.cursor_y_at_spawn,
            "tiempo_explosion_ms": self.explode_ts_ms if self.explode_ts_ms is not None else "",
            "tiempo_adquisicion_ms": (
                self.acquisition_time_ms if self.acquisition_time_ms is not None else ""
            ),
            "longitud_total_trayectoria_px": _round_float(self.total_path_length_px),
            "distancia_linea_recta_px": _round_float(self.straight_line_distance_px),
            "eficiencia_trayectoria": _round_float(self.path_efficiency),
            "cantidad_ingresos_hover": self.hover_entry_count,
            "tiempo_hover_hasta_explosion_ms": self.hover_time_until_explode_ms,
            "cantidad_muestras_traza": self.trace_sample_count,
        }


class SessionRecorder:
    def __init__(self, session_id, configured_target_count, data_output_dir, cursor_trace_hz):
        self.session_id = session_id
        self.configured_target_count = configured_target_count
        self.data_output_dir = Path(data_output_dir)
        self.cursor_trace_hz = max(1, int(cursor_trace_hz))
        self.trace_interval_ms = max(1, round(1000 / self.cursor_trace_hz))

        self.started_at_iso = ""
        self.ended_at_iso = ""
        self.session_start_ticks = 0
        self.next_trace_sample_ms = 0
        self.current_target = None
        self.target_rows = []
        self.cursor_trace_rows = []
        self.event_rows = []
        self.output_dir = None
        self.summary_row = None

    def start(self, now_ms):
        self.started_at_iso = datetime.now().astimezone().isoformat(timespec="seconds")
        self.session_start_ticks = now_ms
        self.next_trace_sample_ms = now_ms
        self.log_event("session_started", now_ms)

    def spawn_target(
        self,
        target_index,
        animal_id,
        spawn_position,
        target_size,
        cursor_position,
        now_ms,
    ):
        spawn_ts_ms = self._relative_ms(now_ms)
        self.current_target = TargetTelemetry(
            session_id=self.session_id,
            target_index=target_index,
            animal_id=animal_id,
            spawn_ts_ms=spawn_ts_ms,
            spawn_x=int(spawn_position[0]),
            spawn_y=int(spawn_position[1]),
            cursor_x_at_spawn=int(cursor_position[0]),
            cursor_y_at_spawn=int(cursor_position[1]),
            target_center_x=spawn_position[0] + target_size[0] / 2,
            target_center_y=spawn_position[1] + target_size[1] / 2,
        )
        self.log_event(
            "target_spawned",
            now_ms,
            target_index=target_index,
            animal_id=animal_id,
            spawn_x=int(spawn_position[0]),
            spawn_y=int(spawn_position[1]),
        )

    def update_hover_state(self, on_target, now_ms):
        if self.current_target is None or self.current_target.explode_ts_ms is not None:
            return

        event_name = self.current_target.update_hover(on_target, self._relative_ms(now_ms))
        if event_name is not None:
            self.log_event(event_name, now_ms, target_index=self.current_target.target_index)

    def sample_cursor(self, now_ms, cursor_position, on_target, hover_elapsed_ms, exploding):
        if self.current_target is None:
            return

        while now_ms >= self.next_trace_sample_ms:
            relative_sample_ms = self._relative_ms(self.next_trace_sample_ms)
            self.cursor_trace_rows.append(
                {
                    "id_sesion": self.session_id,
                    "indice_objetivo": self.current_target.target_index,
                    "tiempo_ms": relative_sample_ms,
                    "x": int(cursor_position[0]),
                    "y": int(cursor_position[1]),
                    "sobre_objetivo": bool(on_target),
                    "tiempo_hover_ms": int(hover_elapsed_ms),
                    "explotando": bool(exploding),
                }
            )

            if not exploding and self.current_target.explode_ts_ms is None:
                self.current_target.add_sample(
                    (int(cursor_position[0]), int(cursor_position[1]))
                )

            self.next_trace_sample_ms += self.trace_interval_ms

    def explode_current_target(self, now_ms):
        if self.current_target is None or self.current_target.explode_ts_ms is not None:
            return

        relative_now_ms = self._relative_ms(now_ms)
        self.current_target.finalize_explosion(relative_now_ms)
        self.target_rows.append(self.current_target)
        self.log_event(
            "target_exploded",
            now_ms,
            target_index=self.current_target.target_index,
            animal_id=self.current_target.animal_id,
        )

    def expire_current_target(self, now_ms):
        if self.current_target is None or any(
            row is self.current_target for row in self.target_rows
        ):
            return

        self.current_target.finalize_incomplete(self._relative_ms(now_ms))
        self.target_rows.append(self.current_target)
        self.log_event(
            "target_timed_out",
            now_ms,
            target_index=self.current_target.target_index,
            animal_id=self.current_target.animal_id,
        )

    def finish(self, status, now_ms):
        if self.current_target is not None and not any(
            row is self.current_target for row in self.target_rows
        ):
            self.current_target.finalize_incomplete(self._relative_ms(now_ms))
            self.target_rows.append(self.current_target)

        self.ended_at_iso = datetime.now().astimezone().isoformat(timespec="seconds")
        self.log_event(
            "session_finished",
            now_ms,
            status=status,
            completed_target_count=self.completed_target_count,
        )
        self.output_dir = self._build_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._write_session_summary(status, now_ms)
        self._write_target_metrics()
        self._write_jsonl(self.output_dir / "cursor_trace.jsonl", self.cursor_trace_rows)
        self._write_jsonl(self.output_dir / "events.jsonl", self.event_rows)

    @property
    def completed_target_count(self):
        return sum(1 for row in self.target_rows if row.explode_ts_ms is not None)

    def _build_output_dir(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.data_output_dir / f"{timestamp}_{self.session_id}"

    def _relative_ms(self, now_ms):
        return max(0, int(now_ms - self.session_start_ticks))

    def log_event(self, event_name, now_ms, **payload):
        translated_payload = {}
        for key, value in payload.items():
            if key == "status":
                translated_payload["estado"] = ESTADOS_EXPORTADOS.get(value, value)
            elif key == "completed_target_count":
                translated_payload["cantidad_objetivos_completada"] = value
            elif key == "target_index":
                translated_payload["indice_objetivo"] = value
            elif key == "animal_id":
                translated_payload["id_animal"] = value
            elif key == "spawn_x":
                translated_payload["posicion_objetivo_x"] = value
            elif key == "spawn_y":
                translated_payload["posicion_objetivo_y"] = value
            else:
                translated_payload[key] = value

        row = {
            "evento": EVENTOS_EXPORTADOS.get(event_name, event_name),
            "id_sesion": self.session_id,
            "tiempo_ms": self._relative_ms(now_ms),
        }
        row.update(translated_payload)
        self.event_rows.append(row)

    def _write_session_summary(self, status, now_ms):
        completed_targets = [row for row in self.target_rows if row.explode_ts_ms is not None]
        acquisition_times = [
            row.acquisition_time_ms for row in completed_targets if row.acquisition_time_ms is not None
        ]
        mean_hover_reentries = _mean(
            [max(0, row.hover_entry_count - 1) for row in completed_targets]
        )
        self.summary_row = {
            "id_sesion": self.session_id,
            "iniciada_en": self.started_at_iso,
            "finalizada_en": self.ended_at_iso,
            "estado": ESTADOS_EXPORTADOS.get(status, status),
            "cantidad_objetivos_configurada": self.configured_target_count,
            "cantidad_objetivos_completada": self.completed_target_count,
            "tasa_completitud": _round_float(
                self.completed_target_count / self.configured_target_count
            ),
            "duracion_sesion_ms": self._relative_ms(now_ms),
            "distancia_total_cursor_px": _round_float(
                sum(row.total_path_length_px for row in self.target_rows)
            ),
            "promedio_tiempo_adquisicion_objetivo_ms": _round_float(_mean(acquisition_times)),
            "mediana_tiempo_adquisicion_objetivo_ms": (
                _round_float(median(acquisition_times)) if acquisition_times else 0.0
            ),
            "promedio_eficiencia_trayectoria": _round_float(
                _mean([row.path_efficiency for row in completed_targets])
            ),
            "promedio_reingresos_hover": _round_float(mean_hover_reentries),
            "promedio_tiempo_hover_hasta_explosion_ms": _round_float(
                _mean([row.hover_time_until_explode_ms for row in completed_targets])
            ),
        }
        self._write_csv(
            self.output_dir / "session_summary.csv",
            SESSION_SUMMARY_FIELDS,
            [self.summary_row],
        )

    def get_target_rows(self):
        return [row.to_row() for row in self.target_rows]

    def _write_target_metrics(self):
        self._write_csv(
            self.output_dir / "target_metrics.csv",
            TARGET_METRIC_FIELDS,
            [row.to_row() for row in self.target_rows],
        )

    def _write_csv(self, path, fieldnames, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _write_jsonl(self, path, rows):
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=True))
                handle.write("\n")
