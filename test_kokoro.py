from kokoro import KPipeline
import soundfile as sf

print("Loading Kokoro model...")

pipeline = KPipeline(lang_code="a")

text = (
    "Welcome to Peniel Devotional. "
    "Let us spend a moment in God's word. "
    "May His word guide your heart today."
)

print("Generating speech...")

for _, _, audio in pipeline(text, voice="af_heart"):
    sf.write("kokoro-test.wav", audio, 24000)

print("Success! Audio saved as kokoro-test.wav")
