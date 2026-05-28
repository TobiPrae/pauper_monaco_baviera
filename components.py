import streamlit as st
from pathlib import Path


def show_logo() -> None:
    """Display the project logo at the top-left of the page.

    Looks for `assets/logo.jpg` or `assets/logo.png` relative to the workspace root.
    """
    logo_jpg = Path("assets") / "logo.jpg"
    logo_png = Path("assets") / "logo.png"
    logo_path = logo_jpg if logo_jpg.exists() else (logo_png if logo_png.exists() else None)
    if not logo_path:
        return


    st.image(str(logo_path), width="stretch")

