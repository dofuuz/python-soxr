import soundfile as sf
import soxr

TARGET_RATE = 16000
CHUNK_SIZE = 96000

# Open input audio file
in_file = sf.SoundFile('very_long.flac', 'r')
source_rate = in_file.samplerate
channels = in_file.channels

# Config ResampleStream
resampler = soxr.ResampleStream(source_rate, TARGET_RATE, channels, dtype='float32')

# Open output audio file
with sf.SoundFile('output.flac', 'w', TARGET_RATE, channels) as out_file:
    while True:
        # Read chunk of audio
        x = in_file.read(CHUNK_SIZE, dtype='float32')
        is_last = (in_file.tell() == in_file.frames)

        # Resample the chunk
        y = resampler.resample_chunk(x, last=is_last)

        # Write to output file
        out_file.write(y)

        if is_last:
            break

in_file.close()
