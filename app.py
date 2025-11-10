"""
Main entry point for the Trail Running GPX Analyzer Streamlit application.

Run with: uv run streamlit run app.py
"""

import streamlit as st

from project.settings import Settings
from project.ui import initialize_session_state, render_gpx_analysis_tab, render_help_tab


def main() -> None:
    """Run the main application."""

    settings = Settings()

    st.set_page_config(
        page_title=settings.app_name,
        page_icon="🏃",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title(f"🏃 {settings.app_name}")
    st.caption(f"バージョン {settings.app_version}")

    st.markdown(
        """
        このアプリはトレイルランニングレース用のGPXファイルを解析し、コース区間ごとの分析や標高計算を行います。
        区間ごとの距離・標高差・傾斜などを可視化できます。GPXファイルをアップロードして詳細なコース情報を確認しましょう。
        """
    )

    initialize_session_state()

    # Create tabs
    tab1, tab2 = st.tabs(["GPX分析", "ヘルプ"])

    with tab1:
        render_gpx_analysis_tab()

    with tab2:
        render_help_tab()


if __name__ == "__main__":
    main()
