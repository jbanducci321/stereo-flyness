import importlib

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "stereo_flyness",
        "stereo_flyness.brain",
        "stereo_flyness.brain.shiu_model",
        "stereo_flyness.brain.shiu_utils",
        "stereo_flyness.game",
        "stereo_flyness.interface",
    ],
)
def test_package_imports(module):
    importlib.import_module(module)
