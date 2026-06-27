import soxr


# Adding info to pytest report header
def pytest_report_header(config):
    rs32 = soxr.ResampleStream(44100, 48000, 1, dtype='float32')
    f32_engine = rs32._csoxr.engine()

    rs64 = soxr.ResampleStream(44100, 48000, 1, dtype='float64')
    f64_engine = rs64._csoxr.engine()

    return [
        f"{soxr.__version__ = }",
        f"{soxr.__libsoxr_version__ = }",
        f"{f32_engine = }",
        f"{f64_engine = }",]
