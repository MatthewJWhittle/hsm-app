"""Cap explainability background rows before SHAP."""

import numpy as np
import pandas as pd

from backend_api.point_explainability import cap_shap_background_rows


def test_cap_shap_background_noop_when_small() -> None:
    df = pd.DataFrame(np.arange(12).reshape(4, 3), columns=list("abc"))
    out = cap_shap_background_rows(df, max_rows=100)
    assert len(out) == 4
    assert out.equals(df)


def test_cap_shap_background_truncates_head() -> None:
    df = pd.DataFrame({"x": range(20)})
    out = cap_shap_background_rows(df, max_rows=5)
    assert len(out) == 5
    assert list(out["x"]) == [0, 1, 2, 3, 4]
