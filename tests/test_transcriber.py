import subprocess
from unittest.mock import patch, MagicMock

import pytest

from src.mixins.transcriber import MixinMediaTranscriber, TranscriberError


class FakeMedia:
    path = "/tmp/test_input.mp4"
    dirname = "/tmp"


class TestMixinMediaTranscriber:
    def setup_method(self):
        class TestMedia(FakeMedia, MixinMediaTranscriber):
            pass

        self.instance = TestMedia()
        self.instance.path = "/tmp/test_input.mp4"
        self.instance.dirname = "/tmp"

    @patch("subprocess.run")
    def test_save_text_calls_transcriber_cli(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        result = self.instance.save_text(ext="txt")

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "transcriber"
        assert args[1] == "-i"
        assert args[2] == "/tmp/test_input.mp4"
        assert args[3] == "-o"
        assert args[5] == "--format"
        assert args[6] == "txt"

    @patch("subprocess.run")
    def test_save_text_raises_on_cli_missing(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(TranscriberError, match="transcriber CLI not found"):
            self.instance.save_text()

    @patch("subprocess.run")
    def test_save_text_raises_on_nonzero_exit(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "transcriber", stderr="error details"
        )

        with pytest.raises(TranscriberError, match="error details"):
            self.instance.save_text()

    @patch("subprocess.run")
    def test_save_text_default_model(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        self.instance.save_text()

        args = mock_run.call_args[0][0]
        assert "--model" in args
        model_idx = args.index("--model") + 1
        assert args[model_idx] == "base"

    @patch("subprocess.run")
    def test_save_text_default_ext_is_txt(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        self.instance.save_text()

        args = mock_run.call_args[0][0]
        fmt_idx = args.index("--format") + 1
        assert args[fmt_idx] == "txt"

    @patch("subprocess.run")
    def test_save_text_passes_initial_prompt(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        self.instance.save_text(initial_prompt="Custom prompt text")

        args = mock_run.call_args[0][0]
        assert "--initial-prompt" in args
        prompt_idx = args.index("--initial-prompt") + 1
        assert args[prompt_idx] == "Custom prompt text"