# Home Assistant: Whisper API Integration von Speech-to-Text

Integration works for Assist pipelines. 

### Requirements:
- A working Whisper API Key (Try your key with curl or something else)

### Configuration:

Remarks:
- Add your own API key
- language MUST be set AND has to be ISO-639-1 format
- There will be an error in the home assistant logs, that configuring stt is not allowed in configuration.yaml - you can ignore this

configuration.yaml:


```
stt:
  - platform: whisper_api_stt
    api_key: ""
    model: "whisper-1"
    language: "en"
```

### Used sources + thanks to:
- sfortis/openai_tts: https://github.com/sfortis/openai_tts


