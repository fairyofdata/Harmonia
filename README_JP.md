<!-- 原本: README_KR.md（韓国語版が原本、英語・日本語は翻訳） · 同期: 2026-11-24 -->

# LocalTTS

[English](README.md) · [한국어](README_KR.md) · [日本語](README_JP.md)

この PC で動く音声合成（TTS）・音声認識（STT）ツールです。クラウド呼び出しも費用もありません。他のプロジェクトから使う道は二つです。

- **HTTP サーバー**：OpenAI API と同じ形式なので `base_url` を変えるだけです（[下記](#サーバーとして使う他のプロジェクトから)）。
- **MCP サーバー**：エージェントがツールとして直接呼びます（[下記](#mcp-で使う他のプロジェクトのエージェントから)）。

## 入っているもの

| 種類 | エンジン | 声の id | 言語 | ライセンス |
|---|---|---|---|---|
| TTS | [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)（GPU） | `jf_alpha` `jf_gongitsune` `jf_nezumi` `jf_tebukuro` `jm_kumo` ほか | 日本語（英語・中国語の声は spacy が必要、下記参照） | Apache-2.0 |
| TTS | [Supertonic-3](https://github.com/supertone-inc/supertonic)（ONNX、GPU があれば GPU） | `st_M1`〜`st_M5`、`st_F1`〜`st_F5` | 31 言語（`lang` で指定：`ko`、`ja`、`en` …） | 重み OpenRAIL-M、SDK MIT |
| TTS | Windows 標準の音声（OneCore） | `win_haruka` `win_ayumi` `win_ichiro`（日本語）、`win_heami`（韓国語） | インストール済みの言語パックによる | Windows |
| STT | Whisper large-v3（GPU fp16） | — | 多言語、言語の自動検出または指定 | MIT |
| 変換 | 日本語 → 韓国人が読むようなハングル読み（`ja_to_hangul`） | — | — | このリポジトリ |

`python -m localtts voices` でこの PC で使える声の一覧を見ます。

Supertonic は語彙にない文字（珍しい漢字など）があるとエラーになります。そのためそういう文字を含む単語は UniDic のかな読みに置き換えて読み、それでも残る文字は抜いて読みます。また一度に処理できる長さに限界があるので、長い文は 80 字の断片に分けて合成し、断片の間に 0.15 秒の間を置きます（空白のない日本語・中国語は文字数で切ります）。

## サーバーとして使う（他のプロジェクトから）

```bash
<LocalTTS フォルダー>\venv\Scripts\python.exe -m localtts serve --port 8880
```

`127.0.0.1` にだけ開くので、外部からは接続できません。

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8880/v1", api_key="local")

# TTS（wav のみ、ffmpeg なし）
wav = client.audio.speech.create(model="local", voice="st_F2", input="안녕하세요",
                                 response_format="wav", extra_body={"lang": "ko"}).content

# 日本語を韓国人が読むようにハングル読みに変えて韓国語の声で読む
wav = client.audio.speech.create(model="local", voice="st_M3", input="明日は晴れるといいね", response_format="wav",
                                 extra_body={"translit": "ja_to_hangul",
                                             "translit_style": {"tsu": "ㅅ", "long_vowel": "keep"}}).content

# STT
with open("clip.wav", "rb") as f:
    r = client.audio.transcriptions.create(model="whisper-large-v3", file=f, response_format="verbose_json")
print(r.text, r.language)
```

OpenAI API にない拡張：

| エンドポイント / フィールド | 説明 |
|---|---|
| `POST /v1/audio/speech` の `translit`、`translit_style` | `ja_to_hangul` の読み変換とその表記方式 |
| `POST /v1/audio/speech` の `lang` | Supertonic の声の言語コード |
| `POST /v1/audio/speech` の `pitch` | Windows の声の高さ（0.0〜2.0） |
| `POST /v1/batch/transcriptions` | `{"files_b64": [...], "language": null}` → 複数のクリップを GPU で一度に書き起こし（1 クリップ約 0.3 秒） |
| `POST /v1/translit` | `{"text": "...", "translit_style": {...}}` → 合成せずに読みだけ変換 |
| `GET /v1/voices` | 声の一覧 |

## MCP で使う（他のプロジェクトのエージェントから）

Claude Code の設定（`~/.claude.json`）の最上位 `mcpServers` に入れると、すべてのプロジェクトで見えます。

```json
"localtts": {
  "type": "stdio",
  "command": "<LocalTTS フォルダー>\\venv\\Scripts\\python.exe",
  "args": ["-m", "localtts_mcp"],
  "env": {}
}
```

`command` は**このプロジェクトの venv の python** でなければなりません。`mcp` と `localtts` はそこにだけ入っていて、サーバーを自動で立ち上げるときもこの python を使います。直したあとはアプリ（または `claude`）を再起動すると反映されます。

`claude` CLI が入っていれば、同じ場所に入れてくれます。`-s user` がないとコマンドを実行したフォルダーでだけ見えます。

```bash
claude mcp add localtts -s user -- <LocalTTS フォルダー>\venv\Scripts\python.exe -m localtts_mcp
```

ツールが五つ付きます。

| ツール | すること |
|---|---|
| `list_voices` | この PC の声の一覧 |
| `synthesize` | 文 → wav ファイルに保存して `{path, seconds, sample_rate}` を返す（音をその場で鳴らしはしません） |
| `transcribe` | 音声ファイル → `{text, language, duration}` |
| `transcribe_many` | 複数のファイルを GPU で一度に（1 クリップ約 0.3 秒） |
| `ja_to_hangul` | 日本語 → ハングル読み |

MCP サーバーは上の HTTP サーバーに要求を渡すだけの薄いプロキシです。サーバーが立っていなければ、**最初の呼び出しでバックグラウンドに立ち上げます。** そのため同時に複数のプロジェクトから呼んでもモデルはこの PC に一組だけ載り、MCP プロセス自体はモデルを持ちません（torch も読み込まないので 0.7 秒で立ち上がります）。このため `localtts_mcp.py` はパッケージの外にあります — `localtts` を import すると torch がついてくるからです。

自動で立ち上げたサーバーは、**MCP クライアントが終わると一緒に落ちることがあります。** MCP クライアントがサーバープロセスをジョブオブジェクトに入れ、終了時にまとめて片付けるためです（確認済み）。もう一度呼べば勝手に上がり、重みはローカルのキャッシュから読むので数秒で済みます。ずっと立てておきたければ `python -m localtts serve` を自分で実行しておけばよく、そのサーバーには MCP は手を出しません。

| 環境変数 | 既定値 |
|---|---|
| `LOCALTTS_URL` | `http://127.0.0.1:8880` |
| `LOCALTTS_OUT_DIR` | `<temp>/localtts`（合成した wav とサーバーのログがたまる場所） |
| `LOCALTTS_AUTOSTART` | `1`（`0` ならサーバーを自分で立てておく必要があります） |
| `LOCALTTS_PYTHON` | この MCP サーバーを実行した python（サーバーを立てるときに使います） |

サーバーが新しく立ったあとの最初の `transcribe` は Whisper の重みを GPU に載せるため 10 秒前後かかり（一番最初の一回は約 3GB をダウンロードします）、その後はすぐに応答します。`synthesize` は 1 秒前後です。

## Python から直接使う

```python
import sys; sys.path.insert(0, r"<LocalTTS フォルダー>")   # またはこの venv で実行
import localtts
audio, sr = localtts.synthesize("こんにちは", voice="jf_alpha")
localtts.save_wav("out.wav", audio, sr)

from localtts.jp2hangul import ja_to_hangul
ja_to_hangul("ありがとう")                       # '아리가토'
ja_to_hangul("ありがとう", {"long_vowel": "keep"})  # '아리가토오'
```

`jp2hangul` は fugashi と unidic-lite さえあれば別の venv からも import できます。

## コマンドライン

```bash
python -m localtts voices
python -m localtts say "こんにちは" -o out.wav --voice jf_alpha
python -m localtts say "こんにちは" -o out.wav --voice st_F1 --translit ja_to_hangul
python -m localtts hangul "東京タワーで待ってる"
python -m localtts transcribe out.wav --language ja
```

## ハングル読み（`ja_to_hangul`）の規則

UniDic（fugashi + unidic-lite）の発音で漢字を読んだあと、韓国人が日本語を読むやり方に近く変えます。公式の外来語表記法ではなく発音の近似です。

| 項目 | 既定値 | `translit_style` で変えられる値 |
|---|---|---|
| `tsu`（つ） | `ㅊ` → 츠 | `ㅅ` → 쓰、`ㅉ` → 쯔 |
| `initial`（語頭の無声音） | `aspirated` → 카·타 | `plain` → 가·다（表記法式） |
| `long_vowel`（長音） | `drop` → 토 | `keep` → 토오 |
| `n_assim`（ㅁ·ㅂ·ㅍ の前の ん） | `false` → ㄴ | `true` → ㅁ |

常に適用される規則：っ → パッチム ㅅ、ん → パッチム ㄴ、ス·ズ → 스·즈、ファ行 → ㅍ、語節間の分かち書き。ラテン文字の区間はそのまま残します。歌詞のような特殊な読み（当て字・ルビ）は辞書の読みと違うことがあります。

## インストール（Windows、Python 3.14）

```bash
py -3.14 -m venv venv
venv\Scripts\python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m pip install --no-deps kokoro
venv\Scripts\python -m pip install --no-deps --ignore-requires-python misaki==0.9.4
venv\Scripts\python -m pip install --no-deps -e .
```

モデルの重み（Whisper large-v3 約 3GB、Kokoro、Supertonic）は初めて使うときに Hugging Face のキャッシュ（`~/.cache/huggingface`）に取得します。GPU メモリは Whisper と Kokoro を一緒に載せても約 4.5GB（RTX 3070 8GB で確認）です。

## テスト

```bash
venv\Scripts\python -X utf8 -m unittest discover -s tests
```

33 個、モデルも GPU も使わず 0.1 秒以内に終わります。検査するのは正解が決まっている二か所です。

- **読みの規則**（`jp2hangul`）：っ·ん のパッチム、ス·ズ、ファ行、拗音、分かち書きのような常に適用される規則と、`translit_style` の四つのオプションを両方の値で一つずつ。オプションの組み合わせ 24 通りすべてについて、**かなが一文字も残らないか**も見ます（新しい規則が既存のかなを取りこぼすとここで捕まります）。
- **長文の分割**（`supertonic_backend._chunks`）：すべての断片が限界以下か、空の断片がないか、文字が消えないか、境界（79/80/81 字）でどう切れるか。

音声そのものは自動では検査できません。耳で確かめるか、合成した wav を Whisper で書き起こして入力と比べる方法を使います（`_chunks` の 80 字の限界もそうして確かめました）。

## 決定記録

設計の決定とその理由は [docs/adr/](docs/adr/README.md)（韓国語）にあります。

## Python 3.14 で回避したこと

- **kokoro** は `numpy==1.26.4` を固定していますが 3.14 用のビルドがありません。そのため `--no-deps` で入れます（最新の numpy で動作確認）。
- **misaki 0.9.4** は 3.13 未満と表示されていますが純粋な Python なのでそのまま使います。
  - kokoro 0.7 のパイプラインと戻り値の形式が違うので、`kokoro_backend` が g2p とモデルを直接呼びます。
- **mojimoji**（Cython、3.14 ビルドなし）は `jaconv` ベースの代替モジュール（`_mojimoji_shim.py`）に置き換えました。
- **spacy** は 3.14 ビルドがないので、英語・中国語の Kokoro の声は使えません。
  - 日本語は spacy なしで動くよう空の代替モジュールを差し込みます。
  - 英語が必要なら Supertonic（`st_*`、`lang="en"`）を使えばよいです。
- **Supertonic の GPU 実行：** パッケージの既定は CPU のみです。onnxruntime-gpu が入っていれば、バックエンドが CUDA 実行プロバイダーをオンにします。
  - 9.5 秒の音声で CPU 9.2 秒 → GPU 0.17 秒に速くなりました。
  - onnxruntime-gpu 1.31 は CUDA 13 の DLL（`cublasLt64_13.dll`）を要求するので、torch cu126 と合う 1.24.1 に固定しました。必要な CUDA・cuDNN の DLL は先に読み込んだ torch が提供します。
- **torch と winrt の順序**：winrt を先に読み込むと torch の DLL 初期化が失敗する（WinError 1114）ので、パッケージは torch を先に読み込みます。

## ライセンス

このリポジトリのコードは [MIT](LICENSE) です。エンジンとモデルの重みは上の「入っているもの」の表に記したそれぞれのライセンスに従います（重みはリポジトリに含まれていません）。
