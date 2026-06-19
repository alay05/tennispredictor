# Deferred Items

## 2026-06-18

- `xgboost==3.2.0` installs through `python3 -m uv sync --group dev --group ml`, but importing the package on this macOS host currently fails because `libxgboost.dylib` cannot load `libomp.dylib`. This plan does not train the XGBoost candidate, so the issue was deferred instead of widening the baseline slice. Revisit before executing `03-03-PLAN.md`.
