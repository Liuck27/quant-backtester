from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "quant_strategy_cpp",
        ["src/cpp/strategy.cpp"],
    ),
]

setup(
    name="quant_strategy_cpp",
    version="0.0.1",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
