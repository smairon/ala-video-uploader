
# HLS uploader

Daemon that publishes completed HLS MPEG-TS segments from a mounted recordings
directory to an S3-compatible bucket. It publishes segments before the playlist,
so a browser never receives a playlist pointing to an unavailable object.

## Local run

Start SeaweedFS and the uploader:

```sh
docker compose up --build
```

The bundled SeaweedFS instance is deliberately limited to one local volume for
development. To discard its test objects and reclaim Docker disk space, run:

```sh
docker compose down -v
```

In another terminal, emulate a recorder. The `--fast` option is useful for a
quick smoke test; omit it to emit media at wall-clock speed.

```sh
uv run python -m scripts.emulator --stream-id camera-001 --fast --duration 30
```

Run the daemon directly instead of Docker:

```sh
export RECORDINGS_DIR="$PWD/data/recordings"
export STATE_DB_PATH="$PWD/data/uploader-state/uploader.sqlite3"
export S3_ENDPOINT_URL=http://localhost:8333
export S3_BUCKET=video
export S3_ACCESS_KEY_ID=admin
export S3_SECRET_ACCESS_KEY=admin
uv run python -m scripts.worker
```

Prometheus metrics are exposed at `http://localhost:8000/metrics`.

## Observability

`docker compose up` also starts local Prometheus and Grafana:

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)

Grafana provisions the Prometheus datasource and the `HLS Uploader Overview`
dashboard automatically. The dashboard shows backlog, oldest pending segment,
active streams, recent stream errors, upload rate, throughput, latency, and
stream lifecycle state.

## Lifecycle guarantees

- A segment is uploaded only after its successor appears in the playlist. The
	current last segment may still be written by the recorder and is left intact.
- If the current last segment keeps the same size and modification time for
	`LAST_SEGMENT_STABLE_SECONDS`, it is uploaded without waiting for a successor.
- At ten hours from the first segment name, the final segment is uploaded and
	the S3 copy of the playlist gains `#EXT-X-ENDLIST`.
- SQLite persists successful S3 acknowledgements before local files are deleted.
- SQLite state is kept outside the shared recordings volume so the recorder
	sees only media files and its own playlist.
- A finalized stream is recorded in SQLite and excluded from further HLS
	publish passes. After playlist retention elapses, the uploader removes its
	local playlist and the empty stream directory.
- A failure in one stream is logged and counted without stopping processing of
	other streams.
- S3 objects are retained indefinitely. The local playlist stays for at least
	24 hours after it is first seen; completed segments are removed after upload.

## Logging

`LOG_LEVEL` controls the root level. Component levels can be configured with
variables such as `LOG_LEVEL_UPLOADER_S3=DEBUG` or
`LOG_LEVEL_UPLOADER_PUBLISHER=DEBUG`.
