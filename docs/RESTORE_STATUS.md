# Trạng thái khôi phục mã nguồn

Cập nhật: 2026-09-24 16:54 — sinh tự động bằng `python tools/restore_status.py --write`, đừng sửa tay.

Bốn mức, xếp theo mức độ tin dùng được của file:

- **A. Khớp bytecode 100%** với bản đã phát hành → dùng y hệt: **32 file**
- **B. Parse được nhưng còn thiếu hàm / còn "hỏng im lặng"** → ĐỪNG tin: **72 file**
- **C. Parse được, đủ hàm, chỉ lệch cách viết** → cần đối chiếu thêm: **11 file**
- **D. Chưa phải Python hợp lệ** → không chạy được: **6 file**

Mức B là nguy hiểm nhất: file import bình thường, chạy bình thường, nhưng có hàm thân đã mất hoặc dịch ra mã sai (kiểu `text = ''.replace(...)` làm rỗng chuỗi). Bộ test `tests/` chỉ phủ được các file đã khôi phục có chủ đích.

## D. Chưa parse được (6)

| file | dòng | lỗi |
|---|---|---|
| `app/services/capcut_draft_builder.py` | ? | không đọc được: invalid syntax (capcut_draft_builder.py, lin |
| `app/services/gemini_translate.py` | ? | không đọc được: cannot assign to function call here. Maybe y |
| `app/services/manual_translate.py` | ? | không đọc được: invalid syntax (manual_translate.py, line 40 |
| `app/services/story_engine.py` | ? | không đọc được: invalid syntax (story_engine.py, line 635) |
| `app/services/system_fonts.py` | ? | không đọc được: invalid syntax (system_fonts.py, line 58) |
| `app/services/voice_engine/zerotts/voices.py` | ? | không đọc được: invalid syntax (voices.py, line 35) |

## B. Parse được nhưng còn thiếu hàm hoặc hỏng im lặng (72)

| file | lệch bytecode | hàm thiếu | hỏng im lặng |
|---|---|---|---|
| `app/ui/widgets/blur_region_editor.py` | 246 | 219 | 0 |
| `app/ui/main_window.py` | 207 | 205 | 0 |
| `app/ui/widgets/story_editor.py` | 182 | 167 | 0 |
| `app/ui/modules/module_story.py` | 126 | 124 | 0 |
| `app/ui/modules/module_caption_tools.py` | 98 | 84 | 0 |
| `app/ui/preview_panel.py` | 79 | 77 | 0 |
| `app/ui/widgets/settings_dialog.py` | 56 | 50 | 0 |
| `app/ui/widgets/manual_translate_dialog.py` | 37 | 35 | 0 |
| `app/ui/widgets/voice_history_dialog.py` | 34 | 33 | 0 |
| `app/ui/widgets/story_youtube_window.py` | 35 | 31 | 0 |
| `app/ui/widgets/story_youtube_dialog.py` | 33 | 29 | 0 |
| `app/ui/widgets/story_bgm_dialog.py` | 31 | 28 | 0 |
| `app/ui/modules/base_module.py` | 27 | 23 | 0 |
| `app/ui/modules/module_trim.py` | 25 | 23 | 0 |
| `app/ui/modules/module_video.py` | 24 | 22 | 0 |
| `app/ui/widgets/story_ai_creator_dialog.py` | 24 | 22 | 0 |
| `app/core/state.py` | 24 | 21 | 0 |
| `app/ui/widgets/texture_library_dialog.py` | 28 | 21 | 0 |
| `app/ui/widgets/queue_list_view.py` | 23 | 20 | 0 |
| `app/ui/widgets/story_voice_casting_dialog.py` | 23 | 20 | 0 |
| `app/ui/widgets/audio_waveform_widget.py` | 22 | 19 | 0 |
| `app/ui/widgets/story_subtitle_dialog.py` | 21 | 19 | 0 |
| `app/ui/modules/module_blur.py` | 20 | 18 | 0 |
| `app/config/theme.py` | 45 | 17 | 0 |
| `app/ui/modules/module_bgm.py` | 21 | 17 | 0 |
| `app/ui/widgets/music_library_dialog.py` | 20 | 17 | 0 |
| `app/ui/widgets/story_projects_dialog.py` | 24 | 17 | 0 |
| `app/ui/widgets/story_prompt_builder_dialog.py` | 20 | 17 | 0 |
| `app/services/render_pipeline.py` | 49 | 16 | 0 |
| `app/ui/widgets/font_picker.py` | 39 | 16 | 0 |
| `app/ui/widgets/story_competitor_dialog.py` | 17 | 15 | 0 |
| `app/ui/widgets/story_web_ai_dialog.py` | 18 | 15 | 0 |
| `app/services/voice_engine/vieneu_engine.py` | 19 | 14 | 0 |
| `app/ui/widgets/story_prompts_dialog.py` | 15 | 13 | 0 |
| `app/services/ffmpeg_renderer.py` | 72 | 12 | 0 |
| `app/ui/widgets/story_ai_video_dialog.py` | 13 | 11 | 0 |
| `app/ui/modules/module_brand.py` | 11 | 9 | 0 |
| `app/ui/modules/module_bypass.py` | 10 | 8 | 0 |
| `app/services/audio_sync_engine.py` | 43 | 7 | 0 |
| `app/ui/widgets/notification_history_dialog.py` | 13 | 6 | 0 |
| `app/services/capcut_cli.py` | 13 | 5 | 0 |
| `app/services/capcut_tts_engine.py` | 31 | 5 | 0 |
| `app/services/cloud_voice.py` | 113 | 5 | 0 |
| `app/services/voice_engine/zerotts/hub.py` | 16 | 5 | 0 |
| `app/ui/widgets/story_tour.py` | 28 | 5 | 0 |
| `app/services/tts_projects.py` | 2 | 4 | 0 |
| `app/services/drag_drop.py` | 9 | 3 | 0 |
| `app/services/story_youtube_service.py` | 35 | 3 | 0 |
| `app/services/translation_projects.py` | 3 | 3 | 0 |
| `app/services/voice_engine/audio_merger.py` | 5 | 3 | 0 |
| `app/services/voice_engine/zerotts/synthesizer.py` | 17 | 3 | 0 |
| `app/services/voice_history.py` | 1 | 3 | 0 |
| `app/ui/action_bar.py` | 5 | 3 | 0 |
| `app/ui/control_panel.py` | 5 | 3 | 0 |
| `app/ui/widgets/update_notice_dialog.py` | 9 | 3 | 0 |
| `app/services/artifact_manifest.py` | 5 | 2 | 0 |
| `app/services/cache_manager.py` | 3 | 2 | 0 |
| `app/services/srt_change_tracker.py` | 3 | 2 | 0 |
| `app/services/story_video_assembler.py` | 18 | 2 | 0 |
| `app/services/voice_engine/zerotts/tokenizer.py` | 19 | 2 | 0 |
| `app/services/capcut_tts_extractor.py` | 7 | 1 | 0 |
| `app/services/language_detector.py` | 5 | 1 | 0 |
| `app/services/srt_utils.py` | 4 | 1 | 0 |
| `app/services/story_ai_creator_service.py` | 29 | 1 | 0 |
| `app/services/story_ass_service.py` | 18 | 1 | 0 |
| `app/services/story_prompt_service.py` | 13 | 1 | 0 |
| `app/services/story_video_service.py` | 27 | 1 | 0 |
| `app/services/translation_memory.py` | 1 | 1 | 0 |
| `app/services/voice_engine/stt_service.py` | 1 | 1 | 0 |
| `app/services/voice_engine/zerotts/chunking.py` | 20 | 1 | 0 |
| `app/services/waveform_service.py` | 4 | 1 | 0 |
| `app/services/whisper_stt.py` | 5 | 1 | 0 |

## C. Đủ hàm, lệch cách viết (11)

| file | lệch bytecode |
|---|---|
| `app/services/voice_engine/zerotts/__init__.py` | 1 |
| `app/services/voice_engine/zerotts/text_norm/__init__.py` | 1 |
| `app/services/voice_engine/downloader.py` | 3 |
| `app/services/voice_engine/voices_config.py` | 3 |
| `app/services/notification_service.py` | 4 |
| `app/services/video_preprocess.py` | 5 |
| `app/services/capcut_export.py` | 6 |
| `app/services/system_notifier.py` | 6 |
| `app/services/voice_engine/zerotts/audio.py` | 12 |
| `app/services/story_sfx_service.py` | 15 |
| `app/services/story_image_service.py` | 34 |

## A. Đã khớp tuyệt đối (32)

- `app/__init__.py`
- `app/config/__init__.py`
- `app/core/__init__.py`
- `app/services/__init__.py`
- `app/services/capcut_common_task_client.py`
- `app/services/demucs_separator.py`
- `app/services/edge_tts_engine.py`
- `app/services/job_workspace.py`
- `app/services/license_service.py`
- `app/services/log_cleaner.py`
- `app/services/media_probe.py`
- `app/services/preset_manager.py`
- `app/services/story_competitor_service.py`
- `app/services/subtitle_layout.py`
- `app/services/trim_ranges.py`
- `app/services/tts_preview.py`
- `app/services/voice_engine/__init__.py`
- `app/services/voice_engine/api_key_manager.py`
- `app/services/voice_engine/file_handler.py`
- `app/services/voice_engine/plugin_base.py`
- `app/services/voice_engine/tts_generator.py`
- `app/services/voice_engine/voice_fetcher.py`
- `app/services/voice_engine/zerotts/cli.py`
- `app/services/voice_engine/zerotts/codec.py`
- `app/services/voice_engine/zerotts/text_norm/vi_normalizer.py`
- `app/services/voice_engine/zerotts_engine.py`
- `app/ui/__init__.py`
- `app/ui/fluent_icons.py`
- `app/ui/modules/module_subtitle.py`
- `app/ui/widgets/__init__.py`
- `app/ui/widgets/story_editor_dialog.py`
- `main.py`

Kiểm chứng lại: `python tools/compare_bytecode.py --all` và `python tests/run_tests.py`.
