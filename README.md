# C2PA manifest placement in Matroska / WebM: interoperability tests

Test files, scripts and results behind [ietf-wg-cellar/matroska-specification#1134](https://github.com/ietf-wg-cellar/matroska-specification/issues/1134): where a C2PA Manifest Store can sit in a Matroska or WebM file without breaking playback, seeking, remuxing or validation.

Run on macOS (arm64) in October 2026 by Scenario. Media are synthetic (ffmpeg test patterns and tones, browser MediaRecorder captures); the manifest is signed with the C2PA SDK's test certificate.

## Placements tested

`scripts/rewrite.py SRC PAYLOAD OUTDIR TAG` writes each variant of a source file. Element positions are rewritten and SeekHead, Cues and CRC-32 are updated, then the result is checked for well-formedness.

| Variant | What is added |
|---|---|
| `A_end` | `Attachments` with one `AttachedFile` (`content_credential.c2pa`, `application/c2pa`) after the last Cluster, plus a SeekHead entry |
| `A_end_noseek` | same, without a SeekHead entry |
| `A_front` | same `Attachments` before the first Cluster |
| `B_tags` | a `Tag` with empty `Targets` (whole Segment) and a `SimpleTag` (`TagName` `C2PA_MANIFEST`, `TagBinary` = manifest), merged into the file's existing `Tags` element |
| `B_tags_end` | the same `Tag` in a new `Tags` element after the last Cluster, plus a SeekHead entry |
| `C_unknown` | the manifest in an unregistered Top-Level Element ID (`0x1C2B5041`) |
| `D_void` | the manifest inside a `Void` element (control) |

`_300k` variants carry a 300 KB manifest.

## Sources (`sources/`)

- `vp9_opus`, `vp8_vorbis`, `vp9_alpha`, `av1_opus`, `av1_only`, `opus_only`, `h264_aac.mkv`: ffmpeg, `scripts/make_sources.sh`
- `ffx_*`, `long1080_vp9_opus` (1080p, 120 s), `mm_*` (mkvmerge `--webm`): `scripts/make_sources2.sh`
- `mr_*`: Chrome MediaRecorder output (`scripts/record_mr.mjs`), which has unknown-size Segment and Clusters. `scripts/mr_tool.py` writes `<name>F` (finalized: sizes made known) and `U_*` variants (manifest appended to the unknown-size Segment); `<name>R` is an `ffmpeg -c copy` remux of the recording.
- `manifest.c2pa`, `manifest_300k.c2pa`: the payloads (`scripts/payload.py`)

## Checks

- Browsers, `<video>` (`el`) and Media Source Extensions (`mse`): load, play, seek. Chrome 154, Chromium 156, Firefox 157, WebKit 27.2 via Playwright (`scripts/run2.mjs`, pages in `scripts/www/`), Safari 26.6.2 via safaridriver (`scripts/run_safari.mjs`).
- VLC 3.0.24 (`scripts/vlccheck.py`), ffprobe and full decode with ffmpeg 9.0.2 (`scripts/ffcheck2.py`), mkvinfo and `mkvmerge -J` 102 (`scripts/mkvcheck.py`), mkvalidator 0.6.0 with and without the WebM profile (`scripts/mvcheck.py`).
- Remux survival: `ffmpeg -c copy` (default mapping and `-map 0`, to `.mkv` and `.webm`) and `mkvmerge` (to `.mkv` and `--webm`), then a search for the manifest bytes in the output.

## Results (`results/`)

`results/comparison.txt` (`scripts/compare_variants.py`) counts files where a variant does worse than its own unsigned source, so failures the source already has (an ffmpeg Opus interleaving quirk in Chromium MSE, for example) don't count:

```
check                                  A_end  A_end_noseek       A_front        B_tags    B_tags_end     C_unknown
chrome 154.0.8037.98                    0/10          0/10          0/10           0/8          0/10          7/10
chromium 156.0.8078.4                   0/10          0/10          0/10           0/8          0/10          7/10
firefox 157.0                           0/10          0/10          0/10           0/8          0/10          0/10
webkit 27.2                             0/10          0/10         10/10           0/8          0/10          0/10
Safari 26.6.2                           0/10          0/10          9/10             -          0/10             -
VLC 3.0.24                              0/16          0/16          0/16             -          0/16         12/16
ffmpeg probe+decode                     0/10           0/8           0/8           0/6           0/9           0/8
mkvinfo / mkvmerge -J                   0/14          0/14          0/14          0/14          0/14         14/14
mkvalidator (new messages)             22/24         24/24         22/24          0/22         22/24         24/24
```

New mkvalidator messages:
- `A_*`: `ERR201 Invalid 'AttachedFile' (FileName, FileMediaType, FileData, FileUID) for profile 'webm'`.
- `B_tags_end`: `Extra Tags found` and a SeekPoint pointing at the other `Tags`, because those files already had a `Tags` element. `B_tags` (merged into the existing one) adds none.

Manifest still present after remuxing:

```
remux                                      A_end  A_end_noseek       A_front        B_tags    B_tags_end
ffmpeg -c copy default -> .mkv              0/14          0/14          0/14          0/14          0/14
ffmpeg -c copy default -> .webm             0/14          0/14          0/14          0/14          0/14
ffmpeg -c copy map0 -> .mkv                14/14          0/14         14/14          0/14          0/14
ffmpeg -c copy map0 -> .webm                0/14          0/14          0/14          0/14          0/14
mkvmerge -> .mkv                           14/14          0/14         14/14         14/14         14/14
mkvmerge -> .webm                          12/12          0/12         12/12         12/12         12/12
```

The per-file browser, VLC, ffmpeg, MKVToolNix and mkvalidator results are in the JSON files next to it, and `results/sum2.txt` has the browser details.

Note that any remux rewrites the bytes the manifest's hash covers, so a manifest that survives one reports a mismatch.
