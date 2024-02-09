"""
Support for Whisper API STT.
"""
from typing import AsyncIterable
import aiohttp
import os
import tempfile
import voluptuous as vol
from homeassistant.components.tts import CONF_LANG
from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    Provider,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import wave
import io


CONF_API_KEY = 'api_key'
DEFAULT_LANG = 'en-US'
OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
CONF_MODEL = 'model'
CONF_URL = 'url'
CONF_PROMPT = 'prompt'
CONF_TEMPERATURE = 'temperature'

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Optional(CONF_LANG, default=DEFAULT_LANG): cv.string,
    vol.Optional(CONF_MODEL, default='whisper-1'): cv.string,
    vol.Optional(CONF_URL, default=None): cv.string,
    vol.Optional(CONF_PROMPT, default=None): cv.string,
    vol.Optional(CONF_TEMPERATURE, default=0): cv.positive_int,
})


async def async_get_engine(hass, config, discovery_info=None):
    """Set up Whisper API STT speech component."""
    api_key = config[CONF_API_KEY]
    language = config.get(CONF_LANG, DEFAULT_LANG)
    model = config.get(CONF_MODEL)
    url = config.get('url')
    prompt = config.get('prompt')
    temperature = config.get('temperature')
    return OpenAISTTProvider(hass, api_key, language, model, url, prompt, temperature)


class OpenAISTTProvider(Provider):
    """The Whisper API STT provider."""

    def __init__(self, hass, api_key, lang, model, url, prompt, temperature):
        """Initialize Whisper API STT provider."""
        self.hass = hass
        self._api_key = api_key
        self._language = lang
        self._model = model
        self._url = url
        self._prompt = prompt
        self._temperature = temperature

    @property
    def default_language(self) -> str:
        """Return the default language."""
        return self._language.split(',')[0]

    @property
    def supported_languages(self) -> list[str]:
        """Return the list of supported languages."""
        return self._language.split(',')

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """Return a list of supported formats."""
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return a list of supported codecs."""
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return a list of supported bitrates."""
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return a list of supported samplerates."""
        return [AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return a list of supported channels."""
        return [AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]) -> SpeechResult:
        data = b''
        async for chunk in stream:
            data += chunk

        if not data:
            return SpeechResult("", SpeechResultState.ERROR)

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                with wave.open(temp_file, 'wb') as wav_file:
                    wav_file.setnchannels(metadata.channel)
                    wav_file.setsampwidth(2)  # 2 bytes per sample
                    wav_file.setframerate(metadata.sample_rate)
                    wav_file.writeframes(data)
                temp_file_path = temp_file.name


            url = self._url or OPENAI_STT_URL

            headers = {
                'Authorization': f'Bearer {self._api_key}',
            }

            file_to_send = open(temp_file_path, 'rb')
            form = aiohttp.FormData()
            form.add_field('file', file_to_send, filename='audio.wav', content_type='audio/wav')
            form.add_field('language', self._language)
            form.add_field('model', self._model)

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form, headers=headers) as response:
                    if response.status == 200:
                        json_response = await response.json()
                        return SpeechResult(json_response["text"], SpeechResultState.SUCCESS)
                    else:
                        text = await response.text()
                        return SpeechResult("", SpeechResultState.ERROR)
        except Exception as e:
            return SpeechResult("", SpeechResultState.ERROR)
        finally:
            if 'file_to_send' in locals():
                file_to_send.close()
            if temp_file_path:
                os.remove(temp_file_path)
