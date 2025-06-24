import sys
import os

# Add the 'src' directory to the Python path so that pytest can find the backend and frontend modules.
# This allows tests in subdirectories of 'tests' to import from 'src' as if 'src' were a top-level package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# If you have global fixtures or hooks, they can also be defined here.
# For example, to automatically use a Qt event loop for all tests in `tests/frontend`:
#
# from pytestqt.qt_compat import qt_api
#
# def pytest_runtest_setup(item):
#     """Hook to setup Qt event loop for tests marked with 'qt_app' or in specific paths."""
#     if 'qt_app' in item.keywords or any(path_marker in item.fspath.strpath for path_marker in ['/frontend/']):
#         if not qt_api.qapp: # Check if QApplication already exists
#             qt_api.QApplication([]) # Create a QApplication instance
#
# def pytest_runtest_teardown(item, nextitem):
#      """Hook to cleanup Qt event loop if needed."""
#      if 'qt_app' in item.keywords or any(path_marker in item.fspath.strpath for path_marker in ['/frontend/']):
#          if qt_api.qapp is not None:
#              # You might not need to explicitly quit it depending on test runner and Qt bindings behavior
#              # qt_api.qapp.quit()
#              # qt_api.qapp = None # Reset for next test if necessary
#              pass

# For now, just path manipulation is the primary goal.
# Ensure that this conftest.py is at the root of your 'tests' directory.
# If your tests are in tests/backend and tests/frontend, and src is at ../src
# relative to this conftest.py, the path adjustment should work.
# If conftest.py is in the project root, then it would be sys.path.insert(0, os.path.abspath('./src'))
# Given the `python -m pytest tests/backend/` command, pytest's root might be the project root.
# Let's adjust assuming this conftest.py is in `tests/` and `src/` is a sibling of `tests/`.

# The previous calculation assumed conftest.py is in tests/
# If pytest is run from project root, and conftest.py is in tests/,
# then `os.path.dirname(__file__)` is `/app/tests`.
# `os.path.join(os.path.dirname(__file__), '../src')` becomes `/app/tests/../src` which is `/app/src`.
# This looks correct.

# An alternative if pytest root is the project directory and conftest.py is in tests/
# would be to reference from the project root.
# However, the current approach is common for tests within a tests/ subdirectory.

# Let's ensure the path added is absolute and correct.
# based on `python -m pytest tests/backend/` the working directory is likely /app
# so `../src` from `tests/conftest.py` would be `tests/../src` -> `src` relative to `/app`
# path_to_add = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
# if path_to_add not in sys.path:
#    sys.path.insert(0, path_to_add)
#
# The initial simple version `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))`
# is generally robust for a conftest.py inside the tests directory.

# Simpler version assuming conftest.py is in `tests/` and `src/` is `../src`
# This is the most common setup.
# current_dir = os.path.dirname(os.path.abspath(__file__))
# src_dir = os.path.abspath(os.path.join(current_dir, '..', 'src'))
# if src_dir not in sys.path:
#    sys.path.insert(0, src_dir)
# The initial one-liner `sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))` is fine.

print(f"Conftest: Adding {os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))} to sys.path")
