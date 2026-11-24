"""CLI.

    python -m harmonia voices
    python -m harmonia say "こんにちは" -o out.wav [--voice jf_alpha] [--speed 1.0] [--translit ja_to_hangul]
    python -m harmonia hangul "こんにちは"
    python -m harmonia transcribe out.wav [--language ja]
    python -m harmonia serve [--port 8880]
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser(prog='harmonia')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('voices')
    say = sub.add_parser('say')
    say.add_argument('text')
    say.add_argument('-o', '--out', required=True)
    say.add_argument('--voice', default='jf_alpha')
    say.add_argument('--speed', type=float, default=1.0)
    say.add_argument('--translit', choices=['ja_to_hangul'])
    say.add_argument('--lang', help="Supertonic voices: language code, e.g. ko, ja, en")
    hangul = sub.add_parser('hangul')
    hangul.add_argument('text')
    tr = sub.add_parser('transcribe')
    tr.add_argument('path')
    tr.add_argument('--language')
    srv = sub.add_parser('serve')
    srv.add_argument('--port', type=int, default=8880)
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding='utf-8')
    if args.cmd == 'voices':
        import harmonia
        for v in harmonia.list_voices():
            print(f"{v['id']:<16} {v['backend']:<8} {v['language']:<6} {v['name']}")
    elif args.cmd == 'say':
        import harmonia
        audio, sr = harmonia.synthesize(args.text, voice=args.voice, speed=args.speed, translit=args.translit,
                                        lang=args.lang)
        harmonia.save_wav(args.out, audio, sr)
        print(f'{args.out} ({len(audio) / sr:.2f}s, {sr} Hz)')
    elif args.cmd == 'hangul':
        from harmonia.jp2hangul import ja_to_hangul
        print(ja_to_hangul(args.text))
    elif args.cmd == 'transcribe':
        from harmonia import stt
        print(json.dumps(stt.transcribe(args.path, language=args.language), ensure_ascii=False))
    elif args.cmd == 'serve':
        from harmonia.server import serve
        serve(port=args.port)


if __name__ == '__main__':
    main()
