from motifmaker.motif import Motif, generate_motif


def test_generate_motif_basic():
    motif = generate_motif(
        {
            "contour": "wave",
            "rhythm_density": "medium",
            "mode": "major",
            "root_pitch": 60,
        }
    )
    assert isinstance(motif, Motif)
    assert len(motif.notes) >= 4
    total_beats = sum(note.duration_beats for note in motif.notes)
    assert 2.0 <= total_beats <= 8.0
    assert all(50 <= note.pitch <= 90 for note in motif.notes)
