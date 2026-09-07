# Public presentation deployment

Nginx serves the approved six-page paper-and-signal interface from the persistent
webroot directory `memoryguard-ui-4692b42`. The business image remains frozen at
8a4e521. API requests keep the existing upstream and scoped authorization.

The workbench was recorded at UI commit4692b42. Subsequent changes update only
landing copy, the public evidence entry, final video, poster and subtitles. The
latest video includes the real service restart; it is not the earlier film.
`ui-manifest.json` lists exact served-file fingerprints. `locations.conf` contains
the static routing snippet; preserve the existing TLS and API proxy configuration.

The pre-change configuration is retained on the server for rollback. The former
video is preserved before the new media files are atomically installed. Workbench
HTML/JS/CSS remain identical to the recorded UI. No application build or full test
suite ran for these presentation changes.

`verification.json` records current public response codes, the downloaded video
fingerprint and range support. It is an availability/integrity check, not a full
release gate. The submission portal status is tracked separately in
`submission/status.json` and is only confirmed after the portal is reread.
