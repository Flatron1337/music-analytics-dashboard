import os
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import pandas as pd
import streamlit as st

from parser import format_seconds

YANDEX_SEARCH_BASE_URL = os.getenv("YANDEX_SEARCH_BASE_URL", "https://music.yandex.ru/search")


def normalize_duplicate_title(title: str) -> str:
    """Нормализует название трека, убирая теги ремастеров, делюксов и версий."""
    t = str(title).strip()
    t = re.sub(
        r"[\(\[\{].*?(?:remaster|deluxe|version|bonus|edit|mix|live|remix|acoustic|instrumental|feat|ft\.).*?[\)\]\}]",
        "",
        t,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[\W_]+", " ", t).strip().lower()


def find_duplicate_groups(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], int, int]:
    """Находит группы потенциальных дубликатов и ремастеров в датасете."""
    if df.empty:
        return [], 0, 0

    temp = df.copy()
    temp["norm_title"] = temp["title_raw"].apply(normalize_duplicate_title)
    temp["norm_artist"] = temp["primary_artist"].astype(str).str.strip().str.lower()
    valid = temp[(temp["norm_title"] != "") & (temp["norm_artist"] != "")]
    grouped = valid.groupby(["norm_artist", "norm_title"]).filter(lambda x: len(x) > 1)

    if grouped.empty:
        return [], 0, 0

    groups_list: List[Dict[str, Any]] = []
    tot_dups = 0
    tot_red_sec = 0

    for (a_key, t_key), grp in grouped.groupby(["norm_artist", "norm_title"]):
        sorted_grp = grp.sort_values(by="id", ascending=True)
        tracks_in_grp: List[Dict[str, Any]] = []
        is_first = True

        for _, row in sorted_grp.iterrows():
            dur = int(row.get("duration_sec", 0))
            tracks_in_grp.append({
                "id": row.get("id"),
                "title": str(row.get("title_raw", "")),
                "artist": str(row.get("artist_raw", "")),
                "duration_sec": dur,
                "duration_fmt": str(row.get("duration_fmt", "")),
                "genre_cluster": str(row.get("genre_cluster", "Other")),
                "is_original": is_first,
            })
            if not is_first:
                tot_dups += 1
                tot_red_sec += dur
            is_first = False

        rep_artist = str(sorted_grp.iloc[0].get("primary_artist", a_key))
        rep_title = str(sorted_grp.iloc[0].get("title_raw", t_key))
        groups_list.append({
            "key": f"{a_key} - {t_key}",
            "artist": rep_artist,
            "title": rep_title,
            "count": len(tracks_in_grp),
            "tracks": tracks_in_grp,
            "redundant_sec": sum(t["duration_sec"] for t in tracks_in_grp[1:]),
        })

    groups_list.sort(key=lambda g: g["count"], reverse=True)
    return groups_list, tot_dups, tot_red_sec


def _render_kpis(tot_dups: int, tot_groups: int, tot_red_sec: int) -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value" style="color: #f59e0b;">{tot_dups:,}</div><div class="metric-label">Потенциальных дубликатов</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{tot_groups:,}</div><div class="metric-label">Групп дубликатов</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value" style="color: #ef4444;">{format_seconds(tot_red_sec)}</div><div class="metric-label">Избыточное время</div></div>',
            unsafe_allow_html=True,
        )


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_stream_url(track_id: str, artist: str, title: str, token: Optional[str]) -> Optional[Dict[str, Any]]:
    import yandex_api
    return yandex_api.get_track_stream_url(track_id, token=token, artist=artist, title=title)


def _render_group_tracks_table(group: Dict[str, Any], group_idx: int) -> None:
    rows = []
    for t in group["tracks"]:
        status = "✅ Первый (оригинал)" if t["is_original"] else "⚠️ Повтор / Версия"
        query_text = str(t["artist"]) + " " + str(t["title"])
        url = f"{YANDEX_SEARCH_BASE_URL}?text={urllib.parse.quote_plus(query_text)}"
        rows.append({
            "Статус": status,
            "№": t["id"],
            "Артист": t["artist"],
            "Название": t["title"],
            "Длительность": t["duration_fmt"],
            "Жанр": t["genre_cluster"],
            "url": url,
        })
    table_df = pd.DataFrame(rows)
    st.dataframe(
        table_df,
        column_config={"url": st.column_config.LinkColumn("Яндекс Музыка", display_text="Слушать ↗")},
        use_container_width=True,
        hide_index=True,
    )

    t_options = [f"№{t['id']} — {t['title']} ({t['duration_fmt']})" for t in group["tracks"]]
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        chosen = st.selectbox("Прослушать аудио версии:", t_options, key=f"dup_sel_{group_idx}")
    with col_btn:
        st.write("")
        play_btn = st.button("▶️ Превью", key=f"dup_btn_{group_idx}")

    if play_btn and chosen:
        t_idx = t_options.index(chosen)
        t_item = group["tracks"][t_idx]
        token = st.session_state.get("yandex_token") or None
        with st.spinner("Загрузка отрывка..."):
            info = _fetch_stream_url(str(t_item["id"]), t_item["artist"], t_item["title"], token)
        if info and info.get("stream_url"):
            st.audio(info["stream_url"])
        else:
            st.warning("Не удалось воспроизвести отрывок этого трека.")


def render_duplicates_tab(df: pd.DataFrame) -> None:
    """Отображает вкладку умного поиска дубликатов и ремастеров."""
    st.markdown("### 🧹 Менеджер дубликатов и ремастеров")
    st.caption("Поиск повторяющихся композиций, ремастеров, делюкс-версий и радио-эдитов для очистки плейлиста.")

    groups, tot_dups, tot_red_sec = find_duplicate_groups(df)
    _render_kpis(tot_dups, len(groups), tot_red_sec)

    if not groups:
        st.success("🎉 Дубликатов не найдено! Ваша медиатека идеально уникальна.")
        return

    st.markdown("---")
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_kw = st.text_input("Поиск по артисту или названию в дубликатах:", key="dup_search_input")
    with col_filter:
        min_versions = st.selectbox("Минимум версий в группе:", [2, 3, 4], index=0, key="dup_min_ver")

    filtered_groups = [g for g in groups if g["count"] >= min_versions]
    if search_kw.strip():
        kw = search_kw.strip().lower()
        filtered_groups = [
            g for g in filtered_groups if kw in g["artist"].lower() or kw in g["title"].lower()
        ]

    st.caption(f"Отображается групп: **{len(filtered_groups):,}** из {len(groups):,}")

    for idx, grp in enumerate(filtered_groups[:40]):
        red_fmt = format_seconds(grp["redundant_sec"])
        header = f"🎵 {grp['artist']} — {grp['title']} ({grp['count']} версий • Лишнее время: {red_fmt})"
        with st.expander(header, expanded=False):
            _render_group_tracks_table(grp, idx)

    export_rows = []
    for g in groups:
        for t in g["tracks"]:
            export_rows.append({
                "group_artist": g["artist"],
                "group_title": g["title"],
                "is_original": t["is_original"],
                "track_id": t["id"],
                "artist": t["artist"],
                "title": t["title"],
                "duration_sec": t["duration_sec"],
                "duration_fmt": t["duration_fmt"],
                "genre_cluster": t["genre_cluster"],
            })
    csv_bytes = pd.DataFrame(export_rows).to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "📥 Скачать список всех дубликатов в CSV",
        data=csv_bytes,
        file_name="playlist_duplicates.csv",
        mime="text/csv",
    )
