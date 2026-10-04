"""Immutable values exchanged between application services."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaylistSegment:
    uri: str
    directives: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MediaPlaylist:
    preamble: tuple[str, ...]
    segments: tuple[PlaylistSegment, ...]
