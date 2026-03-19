import csv
import json
import tempfile
import unittest

from telemetry import SessionRecorder


class SessionRecorderTest(unittest.TestCase):
    def _make_recorder(self, output_dir):
        recorder = SessionRecorder(
            session_id="paciente_01",
            configured_target_count=2,
            data_output_dir=output_dir,
            cursor_trace_hz=20,
        )
        recorder.start(now_ms=1000)
        return recorder

    def test_completed_session_exports_expected_files_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            recorder = self._make_recorder(tmp_dir)
            recorder.spawn_target(
                target_index=1,
                animal_id="perro",
                spawn_position=(100, 200),
                target_size=(400, 100),
                cursor_position=(10, 20),
                now_ms=1000,
            )
            recorder.update_hover_state(True, 1100)
            recorder.sample_cursor(1150, (10, 20), False, 0, False)
            recorder.sample_cursor(1200, (110, 210), True, 100, False)
            recorder.update_hover_state(False, 1250)
            recorder.update_hover_state(True, 1300)
            recorder.sample_cursor(1350, (200, 240), True, 50, False)
            recorder.explode_current_target(1400)

            recorder.spawn_target(
                target_index=2,
                animal_id="gato",
                spawn_position=(300, 200),
                target_size=(400, 100),
                cursor_position=(0, 0),
                now_ms=1500,
            )
            recorder.sample_cursor(1550, (0, 0), False, 0, False)
            recorder.update_hover_state(True, 1600)
            recorder.sample_cursor(1650, (320, 230), True, 50, False)
            recorder.explode_current_target(1700)
            recorder.finish(status="completed", now_ms=1800)

            session_dir = recorder.output_dir
            self.assertTrue((session_dir / "session_summary.csv").exists())
            self.assertTrue((session_dir / "target_metrics.csv").exists())
            self.assertTrue((session_dir / "cursor_trace.jsonl").exists())
            self.assertTrue((session_dir / "events.jsonl").exists())

            with (session_dir / "session_summary.csv").open("r", encoding="utf-8") as handle:
                summary_row = next(csv.DictReader(handle))

            self.assertEqual(summary_row["estado"], "completada")
            self.assertEqual(summary_row["cantidad_objetivos_completada"], "2")
            self.assertEqual(summary_row["cantidad_objetivos_configurada"], "2")
            self.assertEqual(summary_row["tasa_completitud"], "1.0")

            with (session_dir / "target_metrics.csv").open("r", encoding="utf-8") as handle:
                target_rows = list(csv.DictReader(handle))

            self.assertEqual(len(target_rows), 2)
            self.assertEqual(target_rows[0]["cantidad_ingresos_hover"], "2")
            self.assertLessEqual(float(target_rows[0]["eficiencia_trayectoria"]), 1.0)
            self.assertGreaterEqual(float(target_rows[0]["eficiencia_trayectoria"]), 0.0)

            with (session_dir / "events.jsonl").open("r", encoding="utf-8") as handle:
                events = [json.loads(line) for line in handle]

            event_names = [event["evento"] for event in events]
            self.assertIn("sesion_iniciada", event_names)
            self.assertIn("objetivo_aparecido", event_names)
            self.assertIn("hover_iniciado", event_names)
            self.assertIn("hover_interrumpido", event_names)
            self.assertIn("objetivo_explotado", event_names)
            self.assertEqual(event_names[-1], "sesion_finalizada")

    def test_aborted_session_persists_partial_target(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            recorder = self._make_recorder(tmp_dir)
            recorder.spawn_target(
                target_index=1,
                animal_id="oveja",
                spawn_position=(50, 50),
                target_size=(400, 80),
                cursor_position=(25, 25),
                now_ms=1000,
            )
            recorder.sample_cursor(1050, (30, 30), False, 0, False)
            recorder.sample_cursor(1100, (40, 40), False, 0, False)
            recorder.finish(status="aborted", now_ms=1200)

            with (recorder.output_dir / "session_summary.csv").open(
                "r", encoding="utf-8"
            ) as handle:
                summary_row = next(csv.DictReader(handle))
            self.assertEqual(summary_row["estado"], "abortada")
            self.assertEqual(summary_row["cantidad_objetivos_completada"], "0")

            with (recorder.output_dir / "target_metrics.csv").open(
                "r", encoding="utf-8"
            ) as handle:
                target_rows = list(csv.DictReader(handle))
            self.assertEqual(len(target_rows), 1)
            self.assertEqual(target_rows[0]["tiempo_explosion_ms"], "")

    def test_cursor_trace_sampling_is_interval_based(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            recorder = self._make_recorder(tmp_dir)
            recorder.spawn_target(
                target_index=1,
                animal_id="leon",
                spawn_position=(100, 100),
                target_size=(400, 100),
                cursor_position=(0, 0),
                now_ms=1000,
            )
            recorder.sample_cursor(1000, (0, 0), False, 0, False)
            recorder.sample_cursor(1105, (10, 0), False, 0, False)
            recorder.sample_cursor(1220, (20, 0), False, 0, False)
            recorder.finish(status="aborted", now_ms=1300)

            with (recorder.output_dir / "cursor_trace.jsonl").open(
                "r", encoding="utf-8"
            ) as handle:
                samples = [json.loads(line) for line in handle]

            sample_times = [sample["tiempo_ms"] for sample in samples]
            self.assertEqual(sample_times[:5], [0, 50, 100, 150, 200])

    def test_timeout_registra_objetivo_expirado(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            recorder = self._make_recorder(tmp_dir)
            recorder.spawn_target(
                target_index=1,
                animal_id="leon",
                spawn_position=(100, 100),
                target_size=(400, 100),
                cursor_position=(0, 0),
                now_ms=1000,
            )
            recorder.sample_cursor(1050, (20, 20), False, 0, False)
            recorder.expire_current_target(1400)
            recorder.finish(status="completed", now_ms=1500)

            with (recorder.output_dir / "target_metrics.csv").open(
                "r", encoding="utf-8"
            ) as handle:
                target_rows = list(csv.DictReader(handle))
            self.assertEqual(len(target_rows), 1)
            self.assertEqual(target_rows[0]["tiempo_explosion_ms"], "")

            with (recorder.output_dir / "events.jsonl").open("r", encoding="utf-8") as handle:
                events = [json.loads(line) for line in handle]
            event_names = [event["evento"] for event in events]
            self.assertIn("objetivo_expirado", event_names)


if __name__ == "__main__":
    unittest.main()
