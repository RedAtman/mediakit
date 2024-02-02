from functools import lru_cache
import logging
from typing import Any, Protocol

from whisper import Whisper

from config import CONFIG


logger = logging.getLogger()

__all__ = [
    "MixinMediaWhisper",
    "MixinMediaFasterWhisper",
    "MixinMediaWhisperCPP",
]


class MixinMediaWhisperProtocol(Protocol):
    path: str
    dirname: str

    def whisper_model(self) -> Whisper: ...
    def _speech_to_text(self) -> dict: ...
    def speech_to_text(self) -> Any: ...
    def save_text(self, ext: str = "txt") -> Any: ...


class MixinMediaWhisper(MixinMediaWhisperProtocol):
    path: str
    # transcribe_kwargs: dict
    # _speech_to_text: Callable

    @property
    def whisper_model(self) -> Whisper:
        import whisper  # pylint: disable=import-outside-toplevel

        return whisper.load_model(CONFIG.WHISPER_MODEL)

    @property
    def transcribe_kwargs(self) -> dict[str, str]:
        return {
            "initial_prompt": "两条商业金句,条条扎心:\
                1. 商业最大的问题不在商业本身,商业是靠人性打仗的哲学,靠人性脱颖而出的艺术.\
                2. 在80%的时间里,你不是在跟人打交道,而是在和人性打交道.",
            # 引导模型解析对话式语音结果
            # 'initial_prompt': '- 今天星期几？- 星期五。'
            # 'verbose': None,
            # 'temperature': 1.0,  # Set temperature to a float value instead of a string
            # 'compression_ratio_threshold': None,  # Set compression_ratio_threshold to None instead of a string
            # 'logprob_threshold': None,  # Set logprob_threshold to None instead of a string
            # 'no_speech_threshold': None,  # Set no_speech_threshold to None instead of a string
            # 'condition_on_previous_text': False,  # Set condition_on_previous_text to a boolean value instead of \
            # a string
            # 'word_timestamps': False,  # Set word_timestamps to a boolean value instead of a string
        }

    @lru_cache(maxsize=9)
    def _speech_to_text(self):
        # logger.info('Processing media: %s', self.path)
        result = self.whisper_model.transcribe(
            self.path,
            **self.transcribe_kwargs,
        )
        return result

    # @lru_cache(maxsize=9)
    def speech_to_text(self):
        result = self._speech_to_text()
        if isinstance(result, dict):
            return result.get("text", "")
        return result

    def save_text(self, ext: str = "txt"):
        result = self._speech_to_text()
        # with open(self.path, 'w') as file:
        # get srt writer for the current directory
        from whisper.utils import get_writer  # pylint: disable=import-outside-toplevel

        writer = get_writer(ext, self.dirname)
        writer(
            result,
            self.path,
            {
                # "max_line_width": 50, "max_line_count": 1, "highlight_words": False
            },
        )  # add empty dictionary for 'options'
        return result


class MixinMediaFasterWhisper(MixinMediaWhisper):
    """Base on faster_whisper
    - 可基于 VAD 对转录优化 避免幻听(转录结果中不断重复某一段文字)
    - 速度更快
    """

    @property
    def whisper_model(self):
        from faster_whisper import WhisperModel

        return WhisperModel(CONFIG.WHISPER_MODEL, device="cpu")

    @property
    def transcribe_kwargs(self):
        super_kwargs = super().transcribe_kwargs
        return {
            # 避免幻听(转录结果中不断重复某一段文字)常用的一组参数
            # 无声识别的阈值，默认为 0.6。当 no_speech_threshold 高于阈值且 logprob_threshold 低于预设时，\
            # 该片段将被标记为静默。对于非英语长视频来说，建议将其调低，否则经常出现大段的重复识别。
            # 'no_speech_threshold': 0.5,
            # # 转录频次的阈值，默认为 -1.0。当 logprob_threshold 低于预设时，将不对该片段进行转录。建议修改为 None 或更低的值。
            # 'log_prob_threshold': None,
            # # 压缩比的阈值，默认为 2.4。当 compression_ratio_threshold 高于预设时，将不对该片段进行转录。
            # 'compression_ratio_threshold': 2.2,
            # 'beam_size': 5,
            "vad_filter": True,
            # 'vad_parameters': dict(min_silence_duration_ms=500),
            **super_kwargs,
        }

    @lru_cache(maxsize=9)
    def _speech_to_text(self):
        """适配 whisper 的 transcribe 方法返回的result格式"""
        segments, info = super()._speech_to_text()
        logger.info(
            "Detected language '%s' with probability %f",
            info.language,
            info.language_probability,
        )
        # for segment in segments:
        #     logger.info(type(segment), segment.__dict__)
        #     print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
        # return segments, info
        segments = [{"start": i.start, "end": i.end, "text": i.text} for i in segments]
        result = {
            "segments": segments,
            "text": "\n".join([segment["text"] for segment in segments]),
            "language": info.language,
        }
        return result


class MixinMediaWhisperCPP(MixinMediaWhisper):
    """Base on faster_whisper
    可基于 VAD 对转录优化，避免幻听(转录结果中不断重复某一段文字)。
    """

    @property
    def whisper_model(self):
        from whisper_cpp import Whisper  # pylint: disable=import-outside-toplevel

        return Whisper(
            "/Users/nut/Dropbox/dev/github/openai_whisper/whisper.cpp/models/ggml-large-v3.bin"
        )

    @property
    def transcribe_kwargs(self):
        # super_kwargs = super().transcribe_kwargs
        return {
            "diarize": True,
        }

    @lru_cache(maxsize=9)
    def _speech_to_text(self):
        """适配 whisper 的 transcribe 方法返回的result格式"""
        result = super()._speech_to_text()
        # logger.info("Detected language '%s' with probability %f" % (info.language, info.language_probability))
        # for segment in segments:
        #     logger.info(type(segment), segment.__dict__)
        #     print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
        # return segments, info
        # segments =  [{'start': i.start, 'end': i.end, 'text': i.text} for i in segments]
        # result = {
        #     'segments': segments,
        #     'text': '\n'.join([segment['text'] for segment in segments]),
        #     'language': info.language,
        # }
        return result

    def save_text(self, ext="txt"):
        self.whisper_model.output(
            fname_out=self.path,
            output_txt=True,
            # output_csv=True,
            # output_jsn=True, output_lrc=True, output_srt=True, output_vtt=True, log_score=True,
        )
