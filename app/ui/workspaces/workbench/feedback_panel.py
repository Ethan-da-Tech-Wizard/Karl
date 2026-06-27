"""Feedback panel — thumbs-up / thumbs-down / correct callbacks."""

from __future__ import annotations


def on_thumb_up(w) -> None:
    if not w._last_response:
        return
    w.orchestrator.save_feedback("thumbs_up", w._system_prompt)
    w._thumb_btn.setText("✓ saved")
    w._thumb_btn.setEnabled(False)
    w._thumb_down_btn.setEnabled(False)


def on_thumb_down(w) -> None:
    if not w._last_response:
        return
    w.orchestrator.save_feedback("thumbs_down", w._system_prompt)
    w._thumb_down_btn.setText("✗ saved")
    w._thumb_btn.setEnabled(False)
    w._thumb_down_btn.setEnabled(False)


def on_correct(w) -> None:
    w._correct_btn.setText("editing...")
    w._correct_btn.setEnabled(False)
    w._is_correcting = True
    w._input.setPlainText(w._last_response)
    w._input.setFocus()
