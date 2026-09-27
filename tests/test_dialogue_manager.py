from dialogue import dialogue_manager


def test_announce_guess_restores_calibrated_gaze_after_thinking(monkeypatch):
    events = []

    class FakeSpeaker:
        def __init__(self, mini, voice_lang_hint):
            pass

        def say(self, text):
            events.append(("say", text))

    monkeypatch.setattr(dialogue_manager, "Speaker", FakeSpeaker)
    monkeypatch.setattr(
        dialogue_manager,
        "thinking",
        lambda mini: events.append(("thinking", mini)),
    )
    monkeypatch.setattr(
        dialogue_manager,
        "look_down_at_board",
        lambda mini, pitch_deg, yaw_deg: events.append(
            ("restore_gaze", mini, pitch_deg, yaw_deg)
        ),
    )

    mini = object()
    manager = dialogue_manager.DialogueManager(
        mini, gaze_pitch_deg=31.0, gaze_yaw_deg=-12.0
    )
    manager.announce_guess(["rouge", "bleu"])

    assert events == [
        ("thinking", mini),
        ("restore_gaze", mini, 31.0, -12.0),
        ("say", "Je propose : rouge, bleu."),
    ]