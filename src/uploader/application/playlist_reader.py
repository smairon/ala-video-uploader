"""HLS parsing and rendering isolated from filesystem and S3 concerns."""

from uploader.specs.constants import HLS_COMMENT_PREFIX, HLS_ENDLIST_TAG, HLS_LINE_SEPARATOR
from uploader.specs.models import MediaPlaylist, PlaylistSegment


class PlaylistReader:
    """Parses recorder playlists and renders safely publishable versions."""

    def parse(self, text: str) -> MediaPlaylist:
        """Parse URI lines while retaining directives that belong to each segment."""
        preamble: list[str] = []
        pending_directives: list[str] = []
        segments: list[PlaylistSegment] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line == HLS_ENDLIST_TAG:
                continue
            if line.startswith(HLS_COMMENT_PREFIX):
                pending_directives.append(line)
                continue
            if not segments:
                preamble.extend(pending_directives)
            directives = tuple(pending_directives if segments else [])
            segments.append(PlaylistSegment(uri=line, directives=directives))
            pending_directives.clear()

        if not segments:
            preamble.extend(pending_directives)
        return MediaPlaylist(preamble=tuple(preamble), segments=tuple(segments))

    def render(self, playlist: MediaPlaylist, published_uris: set[str], *, finalized: bool) -> str:
        """Render only objects confirmed in S3, optionally adding HLS ENDLIST."""
        lines = list(playlist.preamble)
        for segment in playlist.segments:
            if segment.uri in published_uris:
                lines.extend(segment.directives)
                lines.append(segment.uri)
        if finalized:
            lines.append(HLS_ENDLIST_TAG)
        return HLS_LINE_SEPARATOR.join(lines) + HLS_LINE_SEPARATOR
