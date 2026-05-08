from __future__ import annotations

import argparse
import logging
import sys

from .brain import OpenAICodeBridge
from .config import default_config_toml, load_config, write_default_config
from .injector import CodeInjector
from .tts import SpeechEngine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tek Whisperer tray voice bridge.")
    parser.add_argument("--config", help="Path to a Tek Whisperer TOML config file.")
    parser.add_argument("--init-config", action="store_true", help="Write a default user config file.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing config with --init-config.")
    parser.add_argument("--print-config", action="store_true", help="Print the default config TOML.")
    parser.add_argument(
        "--command",
        help="Send a typed command through OpenAI once instead of starting the tray app.",
    )
    parser.add_argument(
        "--inject",
        action="store_true",
        help="With --command, also inject the generated code using the configured injection mode.",
    )
    parser.add_argument(
        "--speak",
        action="store_true",
        help="With --command, also speak the generated explanation.",
    )
    args = parser.parse_args(argv)

    if args.print_config:
        sys.stdout.write(default_config_toml())
        return 0

    if args.init_config:
        path = write_default_config(args.config, overwrite=args.force)
        print(f"Wrote config to {path}")
        return 0

    config = load_config(args.config)
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.command:
        response = OpenAICodeBridge(config.openai).generate(args.command)
        print(response.spoken)
        if response.code:
            print("\n--- code ---")
            print(response.code)
        if args.inject:
            result = CodeInjector(config.injection).inject(response.code)
            print(f"\nInjection: {result.status} - {result.detail}")
        if args.speak:
            SpeechEngine(config.tts).speak(response.spoken)
        return 0

    from .app import TekWhispererApp

    TekWhispererApp(config).run()
    return 0
