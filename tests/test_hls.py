from uploader.application.playlist_reader import PlaylistReader


def test_render_excludes_unpublished_segment_without_dangling_extinf() -> None:
    reader = PlaylistReader()
    playlist = reader.parse(
        "#EXTM3U\n"
        "#EXT-X-VERSION:3\n"
        "#EXT-X-TARGETDURATION:10\n"
        "#EXTINF:10.0,\n"
        "first.ts\n"
        "#EXTINF:10.0,\n"
        "second.ts\n"
    )

    rendered = reader.render(playlist, {"first.ts"}, finalized=False)

    assert rendered == (
        "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXTINF:10.0,\nfirst.ts\n"
    )


def test_render_can_mark_playlist_as_final() -> None:
    reader = PlaylistReader()
    playlist = reader.parse("#EXTM3U\n#EXTINF:10.0,\nfirst.ts\n")

    assert reader.render(playlist, {"first.ts"}, finalized=True).endswith("#EXT-X-ENDLIST\n")


def test_parse_playlist_without_segments_keeps_global_directives() -> None:
    reader = PlaylistReader()
    playlist = reader.parse("#EXTM3U\n#EXT-X-VERSION:3\n")

    assert playlist.segments == ()
    assert reader.render(playlist, set(), finalized=False) == "#EXTM3U\n#EXT-X-VERSION:3\n"
