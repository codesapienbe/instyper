import pocketsphinx

def test_pocketsphinx():
    ps = pocketsphinx.LiveSpeech(
        verbose=False,
        sampling_rate=16000,
        buffer_size=2048,
        no_search=False,
        full_utt=False
    )
    
    phrases = [str(phrase) for phrase in ps]

    assert len(phrases) > 0
    assert phrases[0] == "hello"

def main():
    test_pocketsphinx()

if __name__ == "__main__":
    main()
