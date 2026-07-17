import unittest

from juno_webapp import BOKEH_AVAILABLE, start_juno_webserver


class JunoWebAppTests(unittest.TestCase):
    def test_webapp_module_is_importable_without_bokeh(self) -> None:
        self.assertIsInstance(BOKEH_AVAILABLE, bool)

    @unittest.skipUnless(not BOKEH_AVAILABLE, "Bokeh ist in dieser Umgebung installiert")
    def test_launcher_explains_missing_bokeh(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Bokeh ist nicht installiert"):
            start_juno_webserver()


if __name__ == "__main__":
    unittest.main()
