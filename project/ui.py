"""
Main UI module for the Trail Running GPX Analyzer application.

This module contains the main user interface logic with tabs for GPX analysis and help.
"""

from pathlib import Path

import streamlit as st
from streamlit.runtime.scriptrunner import RerunException

from project.application_services.gpx_service import GPXService
from project.data_accessors.gpx_loader import GPXLoadError
from project.views.chart_view import ChartView
from project.views.map_view import MapView


def initialize_session_state() -> None:
    """Initialize Streamlit session state variables."""
    if "gpx_service" not in st.session_state:
        st.session_state.gpx_service = GPXService()

    if "current_marker_name" not in st.session_state:
        st.session_state.current_marker_name = ""

    if "current_lat" not in st.session_state:
        st.session_state.current_lat = None

    if "current_lon" not in st.session_state:
        st.session_state.current_lon = None

    if "selected_segment" not in st.session_state:
        st.session_state.selected_segment = None

    if "last_map_click" not in st.session_state:
        st.session_state.last_map_click = None


def render_gpx_upload() -> None:
    """Render GPX file upload section."""
    st.subheader("GPXファイルのアップロード")

    upload_method = st.radio(
        "アップロード方法を選択",
        ["ローカルファイル", "URL"],
        horizontal=True,
    )

    service: GPXService = st.session_state.gpx_service

    if upload_method == "ローカルファイル":
        uploaded_file = st.file_uploader(
            "GPXファイルを選択",
            type=["gpx"],
            help="GPXファイル (最大50MB) をアップロードしてください",
        )

        if uploaded_file is not None:
            # Check if this is a new file by comparing file ID
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if "loaded_file_id" not in st.session_state or st.session_state.loaded_file_id != file_id:
                try:
                    with st.spinner("GPXファイルを読み込み中..."):
                        service.load_from_file(uploaded_file)
                    st.session_state.loaded_file_id = file_id

                    # Show success message with waypoint info
                    st.success("GPXファイルを正常に読み込みました")
                except GPXLoadError as e:
                    st.error(f"エラー: {e!s}")
    else:
        url = st.text_input(
            "GPXファイルのURLを入力",
            placeholder="https://example.com/track.gpx",
        )

        if st.button("URLから読み込み", type="primary"):
            if url:
                try:
                    with st.spinner("GPXファイルをダウンロード中..."):
                        service.load_from_url(url)
                    st.session_state.loaded_file_id = f"url_{url}"

                    # Show success message with waypoint info
                    st.success("GPXファイルを正常に読み込みました")
                except GPXLoadError as e:
                    st.error(f"エラー: {e!s}")
            else:
                st.warning("URLを入力してください")


def render_gpx_stats() -> None:
    """Render GPX statistics section."""
    service: GPXService = st.session_state.gpx_service

    if not service.is_loaded():
        return

    stats = service.get_stats()

    st.subheader("トラック統計")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("総距離", f"{stats.total_distance / 1000:.2f} km")

    with col2:
        st.metric("獲得標高", f"{stats.total_ascent:.0f} m")

    with col3:
        st.metric("下降標高", f"{stats.total_descent:.0f} m")

    with col4:
        st.metric("標高範囲", f"{stats.min_elevation:.0f} - {stats.max_elevation:.0f} m")

    st.caption(f"トラックポイント数: {stats.total_points:,}")


def _render_coordinate_input() -> None:
    """Render coordinate input section."""
    coord_method = st.radio(
        "座標入力方法",
        ["トラッククリック", "緯度経度入力"],
        horizontal=True,
        key="coord_method_radio",
    )

    if coord_method == "緯度経度入力":
        col1, col2 = st.columns(2)
        with col1:
            lat_input = st.number_input(
                "緯度",
                value=st.session_state.current_lat if st.session_state.current_lat is not None else 35.0,
                format="%.6f",
                min_value=-90.0,
                max_value=90.0,
                key="lat_input",
            )
        with col2:
            lon_input = st.number_input(
                "経度",
                value=st.session_state.current_lon if st.session_state.current_lon is not None else 135.0,
                format="%.6f",
                min_value=-180.0,
                max_value=180.0,
                key="lon_input",
            )

        # Update coordinates and clear map click history when using manual input
        if st.session_state.current_lat != lat_input or st.session_state.current_lon != lon_input:
            st.session_state.current_lat = lat_input
            st.session_state.current_lon = lon_input
            st.session_state.last_map_click = None
    # Show current click coordinates if available
    elif st.session_state.current_lat is not None and st.session_state.current_lon is not None:
        st.success(f"選択中の座標: ({st.session_state.current_lat:.6f}, {st.session_state.current_lon:.6f})")
        st.caption("右側の地図上にオレンジ色のマーカーが表示されています")
        st.info("マーカーは最も近いGPXトラックポイントに自動配置されます")
    else:
        st.info("右側の地図上のトラックラインをクリックして座標を指定してください")


def _handle_add_marker(service: GPXService, marker_name: str) -> None:
    """Handle adding a new marker."""
    if not marker_name or not marker_name.strip():
        st.warning("マーカー名を入力してください")
        return

    if st.session_state.current_lat is None or st.session_state.current_lon is None:
        st.warning("座標を指定してください(トラックラインをクリックするか緯度経度を入力)")
        return

    # Validate coordinates are valid numbers
    try:
        lat = float(st.session_state.current_lat)
        lon = float(st.session_state.current_lon)

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            st.error("座標が範囲外です (緯度: -90〜90, 経度: -180〜180)")
            return

        # Add marker to the service (insert before goal)
        service.add_marker(marker_name.strip(), lat, lon, insert_before_last=True)

        # Store success message in session state
        st.session_state.marker_add_success = f"マーカー '{marker_name}' を追加しました"

        # Reset coordinates but keep marker name for consecutive additions
        st.session_state.current_lat = None
        st.session_state.current_lon = None
        st.session_state.last_map_click = None

        st.rerun()

    except RerunException:
        # This is normal - st.rerun() raises this exception to restart the app
        raise
    except (ValueError, TypeError) as e:
        st.error(f"座標の変換エラー: {e!s}")
    except OSError as e:
        st.error(f"マーカー追加エラー: {e!s}")


def _render_markers_list(service: GPXService) -> None:
    """Render list of existing markers."""
    markers = service.get_markers()

    # Always show marker count (even if 0)
    st.write(f"**登録済みマーカー:** {len(markers)}個")

    if not markers:
        st.caption("マーカーが登録されていません")
        return

    for i, marker in enumerate(markers):
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            # Show course information if available
            info_text = (
                f"{i + 1}. {marker.name} "
                f"({marker.latitude:.6f}, {marker.longitude:.6f}) - "
                f"{marker.track_point.distance_from_start / 1000:.2f}km"
            )
            if marker.track_point.course is not None:
                directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
                direction_index = int((marker.track_point.course + 22.5) / 45) % 8
                direction = directions[direction_index]
                info_text += f" [{direction}]"
            st.text(info_text)
        with col2:
            # Move up/down buttons
            subcol1, subcol2 = st.columns(2)
            with subcol1:
                if st.button("↑", key=f"move_up_marker_{i}", help="上に移動", disabled=(i == 0)):
                    service.move_marker_up(i)
                    st.rerun()
            with subcol2:
                if st.button("↓", key=f"move_down_marker_{i}", help="下に移動", disabled=(i == len(markers) - 1)):
                    service.move_marker_down(i)
                    st.rerun()
        with col3:
            if st.button("削除", key=f"delete_marker_{i}", help="マーカーを削除"):
                service.remove_marker(i)
                st.rerun()

    if st.button("すべてのマーカーをクリア", type="secondary", width="stretch"):
        service.clear_markers()
        st.rerun()


def render_marker_input() -> None:
    """Render marker input section."""
    service: GPXService = st.session_state.gpx_service

    if not service.is_loaded():
        return

    st.subheader("マーカー設定")

    # Show success message if marker was just added
    if "marker_add_success" in st.session_state:
        st.success(st.session_state.marker_add_success)
        del st.session_state.marker_add_success

    col1, col2 = st.columns([2, 1])

    with col1:
        marker_name = st.text_input(
            "マーカー名",
            value=st.session_state.current_marker_name,
            placeholder="例: CP1, エイドステーション",
            key="marker_name_input",
        )

    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing

    _render_coordinate_input()

    # Add marker button
    if st.button("マーカーを追加", type="primary", width="stretch", key="add_marker_button"):
        _handle_add_marker(service, marker_name)

    _render_markers_list(service)


def render_map_and_chart() -> None:
    """Render map and elevation chart."""
    service: GPXService = st.session_state.gpx_service

    if not service.is_loaded():
        return

    track_df = service.get_track_dataframe()
    markers = service.get_markers()

    # Map section
    st.subheader("トラックマップ")

    # Prepare pending coordinates for display
    pending_coords = None
    if st.session_state.current_lat is not None and st.session_state.current_lon is not None:
        pending_coords = (st.session_state.current_lat, st.session_state.current_lon)

    map_data = MapView.render_map(
        track_df,
        markers=markers,
        highlight_segment=st.session_state.selected_segment,
        pending_coordinates=pending_coords,
    )

    # Handle map clicks
    if map_data:
        clicked_coords = MapView.get_clicked_coordinates(map_data)

        # Check if this is a new click (avoid duplicate processing)
        if clicked_coords and st.session_state.last_map_click != clicked_coords:
            st.session_state.current_lat = clicked_coords[0]
            st.session_state.current_lon = clicked_coords[1]
            st.session_state.last_map_click = clicked_coords
            st.rerun()

    # Show current selected coordinates on map
    if st.session_state.current_lat is not None and st.session_state.current_lon is not None:
        st.success(
            f"**選択中の座標:** 緯度 {st.session_state.current_lat:.6f}, 経度 {st.session_state.current_lon:.6f}"
        )
        st.caption("左側の「マーカー設定」でマーカー名を入力して、「マーカーを追加」ボタンを押してください")
        st.info("選択した座標から最も近いGPXトラック上のポイントに自動的に配置されます")

    # Elevation chart
    st.subheader("標高プロファイル")

    selected_segment = None
    if st.session_state.selected_segment:
        start_idx, end_idx = st.session_state.selected_segment
        selected_segment = service.get_segment(start_idx, end_idx)

    ChartView.render_elevation_profile(
        track_df,
        markers=markers,
        highlight_segment=selected_segment,
    )


def render_segments_table() -> None:
    """Render segments summary table."""
    service: GPXService = st.session_state.gpx_service

    if not service.is_loaded():
        return

    markers = service.get_markers()
    if len(markers) < 2:
        st.info("2つ以上のマーカーを設定すると、セグメント分析表が表示されます")
        return

    st.subheader("セグメント分析")

    segments_df = service.get_segments_dataframe()

    if not segments_df.is_empty():
        # Display dataframe
        st.dataframe(
            segments_df,
            width="stretch",
            column_config={
                "segment": st.column_config.TextColumn("セグメント", width="small"),
                "start": st.column_config.TextColumn("開始", width="medium"),
                "end": st.column_config.TextColumn("終了", width="medium"),
                "distance_km": st.column_config.NumberColumn("距離 (km)", format="%.2f", width="small"),
                "ascent_m": st.column_config.NumberColumn("獲得標高 (m)", format="%.0f", width="small"),
                "descent_m": st.column_config.NumberColumn("下降標高 (m)", format="%.0f", width="small"),
                "gradient_pct": st.column_config.NumberColumn("平均斜度 (%)", format="%.1f", width="small"),
            },
        )

        # Segment selector for highlighting
        segment_options = [
            f"{i + 1}: {row['start']} → {row['end']}" for i, row in enumerate(segments_df.iter_rows(named=True))
        ]

        # Get current selection
        current_selection = "なし"
        if st.session_state.selected_segment is not None:
            start_idx, end_idx = st.session_state.selected_segment
            if start_idx < len(segment_options) and end_idx == start_idx + 1:
                current_selection = segment_options[start_idx]

        # Get the index of current selection
        all_options = ["なし", *segment_options]
        current_index = all_options.index(current_selection) if current_selection in all_options else 0

        selected = st.selectbox(
            "セグメントをハイライト",
            options=all_options,
            index=current_index,
            key="segment_selector",
        )

        # Update selection and trigger rerun if changed
        new_segment = None
        if selected != "なし":
            segment_idx = segment_options.index(selected)
            new_segment = (segment_idx, segment_idx + 1)

        if new_segment != st.session_state.selected_segment:
            st.session_state.selected_segment = new_segment
            st.rerun()

        # CSV download
        csv_data = segments_df.write_csv()
        st.download_button(
            label="CSVでダウンロード",
            data=csv_data,
            file_name="gpx_segments.csv",
            mime="text/csv",
            width="stretch",
        )


def render_gpx_analysis_tab() -> None:
    """Render the GPX analysis tab."""
    service: GPXService = st.session_state.gpx_service

    render_gpx_upload()

    # Only show the rest of the UI if GPX is loaded
    if not service.is_loaded():
        return

    st.divider()

    render_gpx_stats()

    st.divider()

    col1, col2 = st.columns([1, 2])

    with col1:
        render_marker_input()

    with col2:
        render_map_and_chart()

    st.divider()

    render_segments_table()


def render_help_tab() -> None:
    """Render the help tab with usage instructions."""
    st.header("使い方ガイド")

    # Load usage guide from markdown file
    usage_path = Path(__file__).parent.parent / "usages" / "usage.md"

    try:
        with usage_path.open(encoding="utf-8") as f:
            usage_content = f.read()
        st.markdown(usage_content)
    except FileNotFoundError:
        st.error(f"使用方法ファイルが見つかりません: {usage_path}")
        st.info("詳細な使用方法については、リポジトリのusages/usage.mdを参照してください。")
