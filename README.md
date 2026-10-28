# kokoro

An inference library for [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M). You can [`pip install kokoro`](https://pypi.org/project/kokoro/).

> **Kokoro** is an open-weight TTS model with 82 million parameters. Despite its lightweight architecture, it delivers comparable quality to larger models while being significantly faster and more cost-efficient. With Apache-licensed weights, Kokoro can be deployed anywhere from production environments to personal projects.

## Peniel Kokoro service

This repository is kept separate from the Peniel API so that Python, PyTorch, and the model weights do not become API dependencies. Follow the three sections below in order.

### 1. Set up Kokoro from scratch

Install the prerequisites:

1. Install [Python 3.11](https://www.python.org/downloads/) or Python 3.12 and select **Add Python to PATH** during installation. Kokoro 0.9.4 does not support Python 3.13 or newer.
2. Install [eSpeak NG](https://github.com/espeak-ng/espeak-ng/releases) and ensure its installation folder is on `PATH`.
3. Close and reopen PowerShell, then confirm Python is available:

```powershell
python --version
```

Create an isolated environment and install the service dependencies:

```powershell
cd C:\Users\DELL\Documents\MyProject\personal\omeri\kokoro\peniel-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` once in that window, then activate the environment again.

### 2. Run Kokoro locally

To verify that Kokoro itself can synthesize audio, run the bundled test from the repository root:

```powershell
cd C:\Users\DELL\Documents\MyProject\personal\omeri\kokoro
.\peniel-service\.venv\Scripts\Activate.ps1
python -m pip install -e . soundfile
python test_kokoro.py
```

The first run downloads the model weights. Success creates `kokoro-test.wav` in this directory.

### 3. Start Kokoro as the Peniel service

The service exposes `GET /health` and `POST /v1/audio/speech`, which is the API contract Peniel uses.

```powershell
cd C:\Users\DELL\Documents\MyProject\personal\omeri\kokoro\peniel-service
.\.venv\Scripts\Activate.ps1
$env:KOKORO_SERVICE_API_KEY = "replace-with-a-long-random-secret"
uvicorn main:app --host 0.0.0.0 --port 8000
```

Wait for the initial model download and model loading to complete. In another PowerShell window, verify it:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

It should return `status: ok` and `modelLoaded: True`.

Add the following to the Peniel API's `.env`, using the identical secret on both services:

```env
KOKORO_TTS_URL=http://127.0.0.1:8000
KOKORO_TTS_API_KEY=replace-with-a-long-random-secret
KOKORO_TTS_VOICE=am_michael
```

### Deploy the service to Render

Commit and push this `kokoro` project to the Git repository connected to Render. Then create a **Web Service** with these settings:

| Render setting | Value |
| --- | --- |
| Root Directory | `peniel-service` |
| Runtime | Docker |
| Dockerfile Path | `./Dockerfile` |
| Health Check Path | `/health` |

Add these environment variables in Render:

```env
KOKORO_SERVICE_API_KEY=a-long-random-production-secret
# Optional: avoids Hugging Face Hub anonymous-download limits.
HF_TOKEN=your-read-only-hugging-face-token
```

Do not set `PORT`; Render supplies it and the Dockerfile uses it automatically. After deployment, copy the Render service URL into the Peniel API deployment:

```env
KOKORO_TTS_URL=https://your-kokoro-service.onrender.com
KOKORO_TTS_API_KEY=a-long-random-production-secret
KOKORO_TTS_VOICE=am_michael
```

The Dockerfile has been checked for Render: it installs the native audio dependencies, CPU-only PyTorch, and starts Uvicorn on Render's provided port. The first deployment may take longer while the model is downloaded; use an instance with enough RAM for Python, PyTorch, and the model.

### Usage
You can run this basic cell on [Google Colab](https://colab.research.google.com/). [Listen to samples](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/SAMPLES.md).
```py
!pip install -q kokoro>=0.9.4 soundfile
!apt-get -qq -y install espeak-ng > /dev/null 2>&1
from kokoro import KPipeline
from IPython.display import display, Audio
import soundfile as sf
import torch
pipeline = KPipeline(lang_code='a')
text = '''
[Kokoro](/kˈOkəɹO/) is an open-weight TTS model with 82 million parameters. Despite its lightweight architecture, it delivers comparable quality to larger models while being significantly faster and more cost-efficient. With Apache-licensed weights, [Kokoro](/kˈOkəɹO/) can be deployed anywhere from production environments to personal projects.
'''
generator = pipeline(text, voice='af_heart')
for i, (gs, ps, audio) in enumerate(generator):
    print(i, gs, ps)
    display(Audio(data=audio, rate=24000, autoplay=i==0))
    sf.write(f'{i}.wav', audio, 24000)
```
Under the hood, `kokoro` uses [`misaki`](https://pypi.org/project/misaki/), a G2P library at https://github.com/hexgrad/misaki

### Advanced Usage
You can run this advanced cell on [Google Colab](https://colab.research.google.com/).
```py
# 1️⃣ Install kokoro
!pip install -q kokoro>=0.9.4 soundfile
# 2️⃣ Install espeak, used for English OOD fallback and some non-English languages
!apt-get -qq -y install espeak-ng > /dev/null 2>&1

# 3️⃣ Initalize a pipeline
from kokoro import KPipeline
from IPython.display import display, Audio
import soundfile as sf
import torch
# 🇺🇸 'a' => American English, 🇬🇧 'b' => British English
# 🇪🇸 'e' => Spanish es
# 🇫🇷 'f' => French fr-fr
# 🇮🇳 'h' => Hindi hi
# 🇮🇹 'i' => Italian it
# 🇯🇵 'j' => Japanese: pip install misaki[ja]
# 🇧🇷 'p' => Brazilian Portuguese pt-br
# 🇨🇳 'z' => Mandarin Chinese: pip install misaki[zh]
pipeline = KPipeline(lang_code='a') # <= make sure lang_code matches voice, reference above.

# This text is for demonstration purposes only, unseen during training
text = '''
The sky above the port was the color of television, tuned to a dead channel.
"It's not like I'm using," Case heard someone say, as he shouldered his way through the crowd around the door of the Chat. "It's like my body's developed this massive drug deficiency."
It was a Sprawl voice and a Sprawl joke. The Chatsubo was a bar for professional expatriates; you could drink there for a week and never hear two words in Japanese.

These were to have an enormous impact, not only because they were associated with Constantine, but also because, as in so many other areas, the decisions taken by Constantine (or in his name) were to have great significance for centuries to come. One of the main issues was the shape that Christian churches were to take, since there was not, apparently, a tradition of monumental church buildings when Constantine decided to help the Christian church build a series of truly spectacular structures. The main form that these churches took was that of the basilica, a multipurpose rectangular structure, based ultimately on the earlier Greek stoa, which could be found in most of the great cities of the empire. Christianity, unlike classical polytheism, needed a large interior space for the celebration of its religious services, and the basilica aptly filled that need. We naturally do not know the degree to which the emperor was involved in the design of new churches, but it is tempting to connect this with the secular basilica that Constantine completed in the Roman forum (the so-called Basilica of Maxentius) and the one he probably built in Trier, in connection with his residence in the city at a time when he was still caesar.

[Kokoro](/kˈOkəɹO/) is an open-weight TTS model with 82 million parameters. Despite its lightweight architecture, it delivers comparable quality to larger models while being significantly faster and more cost-efficient. With Apache-licensed weights, [Kokoro](/kˈOkəɹO/) can be deployed anywhere from production environments to personal projects.
'''
# text = '「もしおれがただ偶然、そしてこうしようというつもりでなくここに立っているのなら、ちょっとばかり絶望するところだな」と、そんなことが彼の頭に思い浮かんだ。'
# text = '中國人民不信邪也不怕邪，不惹事也不怕事，任何外國不要指望我們會拿自己的核心利益做交易，不要指望我們會吞下損害我國主權、安全、發展利益的苦果！'
# text = 'Los partidos políticos tradicionales compiten con los populismos y los movimientos asamblearios.'
# text = 'Le dromadaire resplendissant déambulait tranquillement dans les méandres en mastiquant de petites feuilles vernissées.'
# text = 'ट्रांसपोर्टरों की हड़ताल लगातार पांचवें दिन जारी, दिसंबर से इलेक्ट्रॉनिक टोल कलेक्शनल सिस्टम'
# text = "Allora cominciava l'insonnia, o un dormiveglia peggiore dell'insonnia, che talvolta assumeva i caratteri dell'incubo."
# text = 'Elabora relatórios de acompanhamento cronológico para as diferentes unidades do Departamento que propõem contratos.'

# 4️⃣ Generate, display, and save audio files in a loop.
generator = pipeline(
    text, voice='af_heart', # <= change voice here
    speed=1, split_pattern=r'\n+'
)
# Alternatively, load voice tensor directly:
# voice_tensor = torch.load('path/to/voice.pt', weights_only=True)
# generator = pipeline(
#     text, voice=voice_tensor,
#     speed=1, split_pattern=r'\n+'
# )

for i, (gs, ps, audio) in enumerate(generator):
    print(i)  # i => index
    print(gs) # gs => graphemes/text
    print(ps) # ps => phonemes
    display(Audio(data=audio, rate=24000, autoplay=i==0))
    sf.write(f'{i}.wav', audio, 24000) # save each audio file
```

### Windows Installation
To install espeak-ng on Windows:
1. Go to [espeak-ng releases](https://github.com/espeak-ng/espeak-ng/releases)
2. Click on **Latest release** 
3. Download the appropriate `*.msi` file (e.g. **espeak-ng-20191129-b702b03-x64.msi**)
4. Run the downloaded installer

For advanced configuration and usage on Windows, see the [official espeak-ng Windows guide](https://github.com/espeak-ng/espeak-ng/blob/master/docs/guide.md)

### MacOS Apple Silicon GPU Acceleration

On Mac M1/M2/M3/M4 devices, you can explicitly specify the environment variable `PYTORCH_ENABLE_MPS_FALLBACK=1` to enable GPU acceleration.

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 python run-your-kokoro-script.py
```

### Conda Environment
Use the following conda `environment.yml` if you're facing any dependency issues.
```yaml
name: kokoro
channels:
  - defaults
dependencies:
  - python==3.9       
  - libstdcxx~=12.4.0 # Needed to load espeak correctly. Try removing this if you're facing issues with Espeak fallback. 
  - pip:
      - kokoro>=0.3.1
      - soundfile
      - misaki[en]
```

### Acknowledgements
- 🛠️ [@yl4579](https://huggingface.co/yl4579) for architecting StyleTTS 2.
- 🏆 [@Pendrokar](https://huggingface.co/Pendrokar) for adding Kokoro as a contender in the TTS Spaces Arena.
- 📊 Thank you to everyone who contributed synthetic training data.
- ❤️ Special thanks to all compute sponsors.
- 👾 Discord server: https://discord.gg/QuGxSWBfQy
- 🪽 Kokoro is a Japanese word that translates to "heart" or "spirit". Kokoro is also a [character in the Terminator franchise](https://terminator.fandom.com/wiki/Kokoro) along with [Misaki](https://github.com/hexgrad/misaki?tab=readme-ov-file#acknowledgements).

<img src="https://static0.gamerantimages.com/wordpress/wp-content/uploads/2024/08/terminator-zero-41-1.jpg" width="400" alt="kokoro" />
