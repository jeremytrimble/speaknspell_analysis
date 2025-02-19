from spana.speak_and_spell_2019 import SpeakAndSpell2019
from kaitaistruct import KaitaiStream

from spana.file_paths import get_default_image_bytes
import typing

def test1():

    dib = get_default_image_bytes()
    #stream = KaitaiStream(dib)
    sskt = SpeakAndSpell2019.from_bytes(dib)

    for idx,ote in enumerate(sskt.offset_table):
        ote: SpeakAndSpell2019.OffsetTableEntry
        ote.speech_data: SpeakAndSpell2019.SpeechPtr
        print(f"{idx=} {ote.playback_rate=} {ote.speech_data.pointer=}")

    for idx,speech in enumerate(sskt.speeches):
        speech: SpeakAndSpell2019.SpeechData
        frames : typing.Sequence[SpeakAndSpell2019.SpeechFrame] = speech.body
        print(f"{idx=} {frames[0].frame_data.hex()=}")


