import soxr


# Adding info to pytest report header
def pytest_report_header(config):
    rs_hq = soxr.ResampleStream(44100, 48000, 1, quality='HQ')
    hq_engine = rs_hq._csoxr.engine()

    rs_vhq = soxr.ResampleStream(44100, 48000, 1, quality='VHQ')
    vhq_engine = rs_vhq._csoxr.engine()

    return [
        f"{soxr.__version__ = }",
        f"{soxr.__libsoxr_version__ = }",
        f"{hq_engine = }",
        f"{vhq_engine = }",]
