#!/usr/bin/env python3
"""Attaches the master soundtrack to a rendered picture: video stream copied (only its BT.709 colour
tags are asserted in the bitstream), audio encoded
once to AAC-LC 320 kb/s (libfdk_aac when available), both streams starting at t = 0, faststart.

Usage: python3 scripts/mux.py <picture.mp4> <soundtrack.wav> <out.mp4>
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FFMPEG, FFMPEG_ENV  # noqa: E402

pic, wav, out = sys.argv[1:4]
encoders = subprocess.run([FFMPEG, '-hide_banner', '-encoders'], capture_output=True, text=True, env=FFMPEG_ENV).stdout
aac = ['-c:a', 'libfdk_aac', '-profile:a', 'aac_low'] if 'libfdk_aac' in encoders else ['-c:a', 'aac']
subprocess.run(
    [FFMPEG, '-v', 'error', '-y', '-i', pic, '-i', wav, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
     # tag the H.264 VUI as BT.709 limited range in the bitstream itself (lossless, no re-encode)
     '-bsf:v', 'h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0',
     *aac,
     '-b:a', '320k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', '-shortest', out],
    check=True, env=FFMPEG_ENV)
print('muxed', out)
