import tempfile
import unittest

from pdf_export import exportar_sesion_a_pdf
from telemetry import SessionRecorder


class PdfExportTest(unittest.TestCase):
    def _build_session_data(self, output_dir):
        recorder = SessionRecorder(
            session_id="paciente_pdf",
            configured_target_count=1,
            data_output_dir=output_dir,
            cursor_trace_hz=20,
        )
        recorder.start(now_ms=1000)
        recorder.spawn_target(
            target_index=1,
            animal_id="perro",
            spawn_position=(100, 200),
            target_size=(400, 100),
            cursor_position=(10, 20),
            now_ms=1000,
        )
        recorder.sample_cursor(1050, (10, 20), False, 0, False)
        recorder.update_hover_state(True, 1100)
        recorder.sample_cursor(1150, (150, 220), True, 50, False)
        recorder.explode_current_target(1200)
        recorder.finish(status="completed", now_ms=1300)
        return recorder

    def test_exporta_pdf_con_cabecera_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            recorder = self._build_session_data(tmp_dir)
            pdf_path = exportar_sesion_a_pdf(
                directorio_sesion=recorder.output_dir,
                resumen=recorder.summary_row,
                metricas_objetivos=recorder.get_target_rows(),
                traza_cursor=recorder.cursor_trace_rows,
                eventos=recorder.event_rows,
            )

            self.assertTrue(pdf_path.exists())
            self.assertGreater(pdf_path.stat().st_size, 0)
            with pdf_path.open("rb") as handle:
                self.assertEqual(handle.read(4), b"%PDF")


if __name__ == "__main__":
    unittest.main()
