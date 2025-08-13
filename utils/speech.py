import datetime
import logging
import wave

from config import CONFIG
import pyaudio
import pyttsx3
import speech_recognition as sr
from speech_recognition import AudioData
import whisper


logger = logging.getLogger(__name__)


class VoiceAssistant:

    def __init__(self, model: str = CONFIG.WHISPER_MODEL):
        # device = "cuda" if torch.cuda.is_available() else "cpu"
        device = "cpu"
        # self.model = whisper.load_model('medium.en', device=device)
        self.model: whisper.Whisper = whisper.load_model(model, device=device)
        logger.info(f"Loaded model: {self.model}")
        self.speaker: pyttsx3.Engine = pyttsx3.init()
        if not isinstance(self.speaker, pyttsx3.Engine):
            raise TypeError("Not a pyttsx3.Engine")
        self.set_language()
        self.start = True

    def set_language(self, language: str = "zh_CN"):
        voices = self.speaker.getProperty("voices")
        # logger.info(('Available voices:', voices))
        # Look for Chinese (zh-cn) voice
        for voice in voices:
            # logger.debug(('Voice:', voice, voice.id, voice.languages))
            if language in voice.languages:
                logger.info(("Using voice:", voice, voice.id, voice.languages))
                self.speaker.setProperty("voice", voice.id)
                break

    def startup(self):
        self.speaking("""你好 我是语音助理 有什么可以帮助你的？""")

    def transform(self):
        # speaking('Talk')
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.pause_threshold = 0.5
            said: AudioData = r.listen(source)
            try:
                q = r.recognize_google(said, language="zh-CN")
                return q
            except sr.UnknownValueError:
                print("抱歉 我不太理解您的意思")
                return "I am waiting"
            except sr.RequestError:
                print("Service is down.")
                self.transform()
                return "I am waiting"
            except:
                return "I am waiting"

    def whisper_ai(self):
        result = self.model.transcribe("samples/voice.wav", language="zh", fp16=False, verbose=True)
        return result["text"]

    def query_day(self):
        day = datetime.date.today()
        weekday = day.weekday()
        # mapping = {
        #     0:'Monday',1:'Tuesday',2:'Wednesday',3:'Thursday',4:'Friday',5:'Saturday',6:'Sunday'
        # }
        try:
            self.speaking(f"今天是星期{weekday}")
        except Exception as err:
            logger.exception(err)

    def query_time(self):
        time = datetime.datetime.now().strftime("%H:%M:%S")
        self.speaking(f"现在时间是 {time[0:2]} 点 {time[3:5]} 分")

    def speaking(self, text: str):
        self.speaker.say(text)
        self.speaker.runAndWait()

    @staticmethod
    def record():
        """
        Records audio from the default input device and saves it to a WAV file.

        Returns:
            None
        """
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        RECORD_SECONDS = 8
        WAVE_OUTPUT_FILENAME = "samples/voice.wav"

        p = pyaudio.PyAudio()

        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

        print("* recording")
        frames: list[bytes] = []
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data: bytes = stream.read(CHUNK)
            frames.append(data)
        print("* done recording")

        stream.stop_stream()
        stream.close()
        p.terminate()

        with wave.open(WAVE_OUTPUT_FILENAME, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))

    def run(self):
        self.startup()
        while self.start:
            s = self.transform().lower()
            if "你好" in s:
                self.record()
                q = self.whisper_ai().lower()
                print(q)
                if "星期几" in q:
                    self.query_day()
                    continue

                elif "几点" in q:
                    self.query_time()
                    continue

                elif "关机" in q or "shutdown" in q:
                    self.speaking("好的 即将关机")
                    break
                # elif "from wikipedia" in q:
                #     speaking("checking wikipedia")
                #     q = q.replace("wikipedia", "")
                #     result = wikipedia.summary(q,sentences=2)
                #     speaking("found on wikipedia")
                #     speaking(result)
                #     continue


if __name__ == "__main__":
    # usage
    assistant = VoiceAssistant()
    assistant.run()
