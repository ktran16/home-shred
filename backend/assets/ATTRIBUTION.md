# Third-party assets

## vivos_ref_vi.wav

Reference clip that the optional F5-TTS Vietnamese voice coach clones (a
Southern-Vietnamese female speaker). Used as the `ref_audio` in
`app/services/tts_f5.py`.

- **Source:** VIVOS Vietnamese speech corpus (AILAB, VNUHCM — Ho Chi Minh City
  University of Science). Speaker `VIVOSDEV16`, utterance `VIVOSDEV16_177`.
- **License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0
  International (CC BY-NC-SA 4.0) — https://creativecommons.org/licenses/by-nc-sa/4.0/
- **Attribution:** Prof. Vu Hai Quang et al., "VIVOS: A Vietnamese speech corpus."
  AILAB, University of Science, VNU-HCM. https://ailab.hcmus.edu.vn/vivos
- **Modifications:** single utterance extracted, downmixed to mono, resampled
  16 kHz → 24 kHz, peak-normalized.
- **Transcript (`TTS_F5_REF_TEXT`):**
  `nếu thỉnh thoảng có vài ngày nghỉ người thụy điển thường ra đảo chơi.`

**NonCommercial:** this clip (and voices cloned from it) may be used for personal,
non-commercial purposes only, consistent with this self-hosted personal project.
To use the voice coach commercially, replace this file with a clip you are
licensed for and update `TTS_F5_REF_TEXT` to its transcript.
