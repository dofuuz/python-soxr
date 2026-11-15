/*
Python-SoXR
https://github.com/dofuuz/python-soxr

SPDX-FileCopyrightText: (c) 2024 Myungchul Keum
SPDX-License-Identifier: LGPL-2.1-or-later

High quality, one-dimensional sample-rate conversion library for Python.
Python-SoXR is a Python wrapper of libsoxr.
*/

#include <stdint.h>
#include <algorithm>
#include <cmath>
#include <memory>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>

#include <soxr.h>

#include "csoxr_version.h"


using std::make_unique;

namespace nb = nanobind;
using namespace nb::literals;
using nb::ndarray;


template <typename T> constexpr soxr_datatype_t to_i_dtype = [] {
    static_assert(sizeof(T) == 0, "Unsupported type for SOXR");
}();
template <> constexpr soxr_datatype_t to_i_dtype<float>   = SOXR_FLOAT32_I;
template <> constexpr soxr_datatype_t to_i_dtype<double>  = SOXR_FLOAT64_I;
template <> constexpr soxr_datatype_t to_i_dtype<int32_t> = SOXR_INT32_I;
template <> constexpr soxr_datatype_t to_i_dtype<int16_t> = SOXR_INT16_I;

template <typename T> constexpr soxr_datatype_t to_s_dtype = [] {
    static_assert(sizeof(T) == 0, "Unsupported type for SOXR");
}();
template <> constexpr soxr_datatype_t to_s_dtype<float>   = SOXR_FLOAT32_S;
template <> constexpr soxr_datatype_t to_s_dtype<double>  = SOXR_FLOAT64_S;
template <> constexpr soxr_datatype_t to_s_dtype<int32_t> = SOXR_INT32_S;
template <> constexpr soxr_datatype_t to_s_dtype<int16_t> = SOXR_INT16_S;


// libsoxr hangs or crashes with I/O ratio out of this range. (also rejects NaN)
// Bundled libsoxr has the same check. This is mainly for external libsoxr.
static double check_io_ratio(double in_rate, double out_rate) {
    if (!(in_rate > 0 && out_rate > 0))
        throw std::invalid_argument("Sample rate should be over 0");

    const double io_ratio = in_rate / out_rate;
    if (!(4e-6 < io_ratio && io_ratio < 1e9))
        throw std::invalid_argument("I/O ratio out of range");

    return io_ratio;
}


// libsoxr becomes much slower when input is long. (see GH PR #39)
// Divide input so neither input nor output exceeds DIV_LEN frames per call.
static size_t calc_div_len(double io_ratio) {
    constexpr double DIV_LEN = 32768;
    return std::max(1., DIV_LEN * std::min(1., io_ratio));
}


class CSoxr {
    soxr_t _soxr = nullptr;
    double _io_ratio;           // current in_rate/out_rate
    std::vector<uint8_t> _y_buf;    // output buffer, reused across process() calls

public:
    const double _in_rate;
    const double _out_rate;
    const soxr_datatype_t _ntype;
    const unsigned _channels;
    bool _ended = false;

    CSoxr(double in_rate, double out_rate, unsigned num_channels,
          soxr_datatype_t ntype, unsigned long quality, bool vr) :
            _in_rate(in_rate),
            _out_rate(out_rate),
            _io_ratio(check_io_ratio(in_rate, out_rate)),
            _ntype(ntype),
            _channels(num_channels) {
        soxr_error_t err = NULL;
        soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
        soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, vr ? SOXR_VR : 0);

        _soxr = soxr_create(
            in_rate, out_rate, num_channels,
            &err, &io_spec, &quality_spec, NULL);

        if (err != NULL) {
            throw std::runtime_error(err);
        }
    }

    ~CSoxr() {
        soxr_delete(_soxr);
    }

    template <typename T>
    auto process(
            ndarray<const T, nb::ndim<2>, nb::c_contig, nb::device::cpu> x,
            bool last=false) {
        const unsigned channels = x.shape(1);

        if (_ended)
            throw std::runtime_error("Input after last input");

        if (channels != _channels)
            throw std::invalid_argument("Channel num mismatch");

        constexpr soxr_datatype_t ntype = to_i_dtype<T>;

        if (ntype != _ntype)
            throw nb::type_error("Data type mismatch");

        const size_t frame_bytes = sizeof(T) * channels;
        const size_t ilen = x.shape(0);
        size_t out_pos = 0;

        soxr_error_t err = NULL;
        {
            nb::gil_scoped_release release;

            // Copying from a resizing buffer ensures the lowest output delay provided by libsoxr.
            // +2: flush output is the estimate rounded, so +1 often fills the buffer and regrows it.
            size_t req_len = soxr_delay(_soxr) + ilen / _io_ratio + 2;

            // divide long input and process (see calc_div_len())
            const size_t div_len = calc_div_len(_io_ratio);
            for (size_t idx = 0; idx < ilen && !err; idx += div_len) {
                size_t in_len = std::min(div_len, ilen-idx);

                // get all output, growing the output buffer as needed
                while (true) {
                    if (_y_buf.size() < req_len * frame_bytes)
                        _y_buf.resize(req_len * frame_bytes);
                    const size_t olen = _y_buf.size() / frame_bytes;

                    size_t odone = 0;
                    err = soxr_process(
                        _soxr,
                        &x.data()[idx * channels], in_len, NULL,
                        &_y_buf[out_pos * frame_bytes], olen-out_pos, &odone);
                    out_pos += odone;
                    in_len = 0;     // soxr takes whole input at once

                    if (err || out_pos < olen) break;

                    // output buffer full, there may be more (e.g. VR mode)
                    req_len = olen * 2;
                }
            }

            // signal end of input and flush
            if (last && !err) {
                _ended = true;

                while (true) {
                    if (_y_buf.size() < req_len * frame_bytes)
                        _y_buf.resize(req_len * frame_bytes);
                    const size_t olen = _y_buf.size() / frame_bytes;

                    size_t odone = 0;
                    err = soxr_process(
                        _soxr,
                        NULL, 0, NULL,
                        &_y_buf[out_pos * frame_bytes], olen-out_pos, &odone);
                    out_pos += odone;

                    if (err || out_pos < olen) break;

                    // output buffer full, there may be more
                    req_len = olen * 2;
                }
            }
        }

        if (err) {
            throw std::runtime_error(err);
        }

        // Return a copy
        T *y = reinterpret_cast<T*>(_y_buf.data());
        return ndarray<nb::numpy, T>(y, { out_pos, channels }).cast();
    }

    size_t num_clips() { return *soxr_num_clips(_soxr); }
    double delay() { return soxr_delay(_soxr); }
    char const * engine() { return soxr_engine(_soxr); }

    void clear() {
        soxr_error_t err = soxr_clear(_soxr);
        if (err != NULL) throw std::runtime_error(err);
        _ended = false;
        _io_ratio = _in_rate / _out_rate;   // soxr_clear() resets I/O ratio
    }

    void set_io_ratio(double in_rate, double out_rate, int64_t slew_len) {
        const double io_ratio = check_io_ratio(in_rate, out_rate);
        if (slew_len < 0 || INT32_MAX < slew_len)   // libsoxr handles it as int
            throw std::invalid_argument("slew_len out of range");

        soxr_error_t err = soxr_set_io_ratio(_soxr, io_ratio, slew_len);
        if (err != NULL) throw std::runtime_error(err);
        _io_ratio = io_ratio;
    }
};


// Divide long input and process. (see calc_div_len())
template <typename T>
auto csoxr_divide_proc(
        double in_rate, double out_rate,
        ndarray<const T, nb::ndim<2>, nb::c_contig, nb::device::cpu> x,
        unsigned long quality) {
    check_io_ratio(in_rate, out_rate);

    const unsigned channels = x.shape(1);

    soxr_error_t err = NULL;

    T *y = nullptr;
    size_t out_pos = 0;
    do {
        nb::gil_scoped_release release;

        constexpr soxr_datatype_t ntype = to_i_dtype<T>;

        // init soxr
        const soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
        const soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, 0);

        soxr_t soxr = soxr_create(
            in_rate, out_rate, channels,
            &err, &io_spec, &quality_spec, NULL);

        if (err) break;

        // alloc
        const size_t ilen = x.shape(0);
        const size_t olen = ilen * out_rate / in_rate + 1;
        const size_t div_len = calc_div_len(in_rate / out_rate);
        y = new T[olen * channels] { 0 };

        // divide long input and process
        size_t odone = 0;
        for (size_t idx = 0; idx < ilen; idx += div_len) {
            err = soxr_process(
                soxr,
                &x.data()[idx*channels], std::min(div_len, ilen-idx), NULL,
                &y[out_pos*channels], olen-out_pos, &odone);
            out_pos += odone;
        }

        // flush
        err = soxr_process(
            soxr,
            NULL, 0, NULL,
            &y[out_pos*channels], olen-out_pos, &odone);
        out_pos += odone;

        // destruct
        soxr_delete(soxr);
    } while (false);

    if (err) {
        delete[] y;
        throw std::runtime_error(err);
    }

    // Delete 'y' when the 'owner' capsule expires
    nb::capsule owner(y, [](void *p) noexcept {
        delete[] (T *) p;
    });
    return ndarray<nb::numpy, T>(y, { out_pos, channels }, owner);
}


// split channel memory I/O (e.g. Fortran order)
template <typename T>
auto csoxr_split_ch(
        double in_rate, double out_rate,
        ndarray<const T, nb::ndim<2>, nb::device::cpu> x,
        unsigned long quality) {
    check_io_ratio(in_rate, out_rate);

    const size_t ilen = x.shape(0);
    const size_t olen = ilen * out_rate / in_rate + 1;
    const unsigned channels = x.shape(1);

    if (ilen != 0 && x.stride(0) != 1)
        throw std::invalid_argument("Data not contiguous");

    soxr_error_t err = NULL;

    T *y = nullptr;
    size_t out_pos = 0;
    do {
        nb::gil_scoped_release release;

        constexpr soxr_datatype_t ntype = to_s_dtype<T>;

        // init soxr
        const soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
        const soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, 0);

        soxr_t soxr = soxr_create(
            in_rate, out_rate, channels,
            &err, &io_spec, &quality_spec, NULL);

        if (err) break;

        // alloc
        const size_t div_len = calc_div_len(in_rate / out_rate);
        y = new T[olen * channels] { 0 };

        const int64_t st = x.stride(1);
        auto ibuf_ptrs = make_unique<const T*[]>(channels);
        auto obuf_ptrs = make_unique<T*[]>(channels);

        // divide long input and process
        size_t odone = 0;
        for (size_t idx = 0; idx < ilen; idx += div_len) {
            // get pointers to each channel i/o
            for (size_t ch = 0; ch < channels; ++ch) {
                ibuf_ptrs[ch] = &x.data()[st * ch + idx];
                obuf_ptrs[ch] = &y[olen * ch + out_pos];
            }

            err = soxr_process(
                soxr,
                ibuf_ptrs.get(), std::min(div_len, ilen-idx), NULL,
                obuf_ptrs.get(), olen-out_pos, &odone);
            out_pos += odone;
        }

        // flush
        for (size_t ch = 0; ch < channels; ++ch) {
            obuf_ptrs[ch] = &y[olen * ch + out_pos];
        }
        err = soxr_process(
            soxr,
            NULL, 0, NULL,
            obuf_ptrs.get(), olen-out_pos, &odone);
        out_pos += odone;

        // destruct
        soxr_delete(soxr);
    } while (false);

    if (err) {
        delete[] y;
        throw std::runtime_error(err);
    }

    // Delete 'y' when the 'owner' capsule expires
    nb::capsule owner(y, [](void *p) noexcept {
       delete[] (T *) p;
    });
    return ndarray<nb::numpy, T>(y, { out_pos, channels }, owner, { (int64_t)1, (int64_t)olen });
}


template <typename T>
auto csoxr_oneshot(
        double in_rate, double out_rate,
        ndarray<const T, nb::ndim<2>, nb::c_contig, nb::device::cpu> x,
        unsigned long quality) {
    check_io_ratio(in_rate, out_rate);

    const size_t ilen = x.shape(0);
    const size_t olen = ilen * out_rate / in_rate + 1;
    unsigned channels = x.shape(1);

    constexpr soxr_datatype_t ntype = to_i_dtype<T>;

    // make soxr config
    soxr_error_t err = NULL;
    const soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
    const soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, 0);

    size_t odone = 0;
    T *y = nullptr;
    {
        nb::gil_scoped_release release;

        y = new T[olen * channels] { 0 };

        err = soxr_oneshot(
            in_rate, out_rate, channels,
            x.data(), ilen, NULL,
            y, olen, &odone,
            &io_spec, &quality_spec, NULL);
    }

    if (err) {
        delete[] y;
        throw std::runtime_error(err);
    }

    // Delete 'y' when the 'owner' capsule expires
    nb::capsule owner(y, [](void *p) noexcept {
       delete[] (T *) p;
    });
    return ndarray<nb::numpy, T>(y, { odone, channels }, owner);
}


NB_MODULE(soxr_ext, m) {
    m.def("libsoxr_version", libsoxr_version);

    nb::class_<CSoxr>(m, "CSoxr")
        .def_ro("in_rate", &CSoxr::_in_rate)
        .def_ro("out_rate", &CSoxr::_out_rate)
        .def_ro("ntype", &CSoxr::_ntype)
        .def_ro("channels", &CSoxr::_channels)
        .def_ro("ended", &CSoxr::_ended)
        .def(nb::init<double, double, unsigned, soxr_datatype_t, unsigned long, bool>())
        .def("process_float32", &CSoxr::process<float>)
        .def("process_float64", &CSoxr::process<double>)
        .def("process_int32", &CSoxr::process<int32_t>)
        .def("process_int16", &CSoxr::process<int16_t>)
        .def("num_clips", &CSoxr::num_clips)
        .def("delay", &CSoxr::delay)
        .def("engine", &CSoxr::engine)
        .def("clear", &CSoxr::clear)
        .def("set_io_ratio", &CSoxr::set_io_ratio);

    m.def("csoxr_divide_proc_float32", csoxr_divide_proc<float>);
    m.def("csoxr_divide_proc_float64", csoxr_divide_proc<double>);
    m.def("csoxr_divide_proc_int32", csoxr_divide_proc<int32_t>);
    m.def("csoxr_divide_proc_int16", csoxr_divide_proc<int16_t>);

    m.def("csoxr_split_ch_float32", csoxr_split_ch<float>);
    m.def("csoxr_split_ch_float64", csoxr_split_ch<double>);
    m.def("csoxr_split_ch_int32", csoxr_split_ch<int32_t>);
    m.def("csoxr_split_ch_int16", csoxr_split_ch<int16_t>);

    m.def("csoxr_oneshot_float32", csoxr_oneshot<float>);
    m.def("csoxr_oneshot_float64", csoxr_oneshot<double>);
    m.def("csoxr_oneshot_int32", csoxr_oneshot<int32_t>);
    m.def("csoxr_oneshot_int16", csoxr_oneshot<int16_t>);

    nb::enum_<soxr_datatype_t>(m, "soxr_datatype_t")
        .value("SOXR_FLOAT32_I", SOXR_FLOAT32_I)
        .value("SOXR_FLOAT64_I", SOXR_FLOAT64_I)
        .value("SOXR_INT32_I", SOXR_INT32_I)
        .value("SOXR_INT16_I", SOXR_INT16_I)
        .export_values();
    
    m.attr("QQ") = SOXR_QQ;
    m.attr("LQ") = SOXR_LQ;
    m.attr("MQ") = SOXR_MQ;
    m.attr("HQ") = SOXR_HQ;
    m.attr("VHQ") = SOXR_VHQ;
}
