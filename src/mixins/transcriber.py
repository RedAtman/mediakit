import logging
import subprocess
from typing import Any

from config import CONFIG

logger = logging.getLogger()

__all__ = [
    "MixinMediaTranscriber",
    "TranscriberError",
]


class TranscriberError(Exception):
    pass


class MixinMediaTranscriber:
    path: str
    dirname: str

    def save_text(
        self,
        ext: str = "txt",
        incremental: bool = False,
        initial_prompt: str | None = None,
        **kwargs: Any,
    ) -> bool:
        cmd = self._build_command(ext, initial_prompt)
        logger.debug("Running: %s", " ".join(cmd))

        try:
            if incremental:
                self._run_streaming(cmd)
            else:
                self._run_simple(cmd)
        except FileNotFoundError:
            raise TranscriberError(
                "transcriber CLI not found. Install:\n"
                "  brew install RedAtman/tap/transcriber"
            ) from None
        except subprocess.CalledProcessError as exc:
            raise TranscriberError(
                f"transcriber failed (exit {exc.returncode}):\n{exc.stderr}"
            ) from None

        return True

    def _build_command(
        self,
        ext: str,
        initial_prompt: str | None = None,
    ) -> list[str]:
        cmd = [
            "transcriber",
            "-i", self.path,
            "-o", self.dirname,
            "--format", ext,
            "--model", CONFIG.TRANSCRIBER_MODEL,
        ]

        prompt = initial_prompt or CONFIG.TRANSCRIBER_INITIAL_PROMPT
        if prompt:
            cmd.extend(["--initial-prompt", prompt])

        return cmd

    def _run_simple(self, cmd: list[str]) -> None:
        subprocess.run(
            cmd + ["--no-streaming"],
            check=True,
            capture_output=True,
            text=True,
        )

    def _run_streaming(self, cmd: list[str]) -> None:
        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as proc:
                for line in proc.stdout or []:
                    line = line.strip()
                    if line:
                        logger.info("[transcriber] %s", line)

                retcode = proc.wait()
                if retcode != 0:
                    stderr_val = proc.stderr.read() if hasattr(proc.stderr, 'read') else str(proc.stderr)
                    raise subprocess.CalledProcessError(
                        retcode, cmd, stderr=stderr_val,
                    )
        except FileNotFoundError:
            raise
        except Exception:
            logger.warning(
                "Streaming mode failed, falling back to file-based output"
            )
            self._run_simple(cmd)