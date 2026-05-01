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


class CSoxr {
    soxr_t _soxr = nullptr;
    double _oi_ratio;
    std::unique_ptr<uint8_t[]> _y_buf;
    size_t _y_buf_bytes = 0;
    size_t _olen = 0;

public:
    const double _in_rate;
    const double _out_rate;
    const soxr_datatype_t _ntype;
    const unsigned _channels;
    const size_t _div_len;
    bool _ended = false;

    CSoxr(double in_rate, double out_rate, unsigned num_channels,
          soxr_datatype_t ntype, unsigned long quality, bool vr) :
            _in_rate(in_rate),
            _out_rate(out_rate),
            _oi_ratio(out_rate / in_rate),
            _ntype(ntype),
            _channels(num_channels),
            _div_len(std::max(1000., 48000 * _in_rate / _out_rate)) {
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
    T* _resize_ybuf(size_t req_size, bool copy) {
        if (_y_buf && req_size < _y_buf_bytes)
            return reinterpret_cast<T*>(_y_buf.get());

        // Grow to next power of 2
        size_t new_size = 1024;
        while (new_size < req_size) new_size <<= 1;
        // size_t new_size = req_size;

        auto new_buf = std::make_unique<uint8_t[]>(new_size);
        if (copy && _y_buf) {
            std::copy_n(_y_buf.get(), _y_buf_bytes, new_buf.get());
        }
        _y_buf = std::move(new_buf);
        _y_buf_bytes = new_size;
        _olen = _y_buf_bytes / (sizeof(T) * _channels);

        // printf("Realloc output buffer: %zu bytes\n", new_size);
        // fflush(stdout);
        return reinterpret_cast<T*>(_y_buf.get());
    }

    template <typename T>
    T* _flush(soxr_in_t input, size_t& out_pos) {
        // flush until no more output
        T* y = reinterpret_cast<T*>(_y_buf.get());
        size_t odone = 0;
        // int cnt = 0;
        do {
            if (_olen <= out_pos) {
                // printf("_flush Realloc cnt = %d\n", ++cnt);
                y = _resize_ybuf<T>(_y_buf_bytes * 2, true);
            }
            soxr_error_t err = soxr_process(
                _soxr,
                input, 0, NULL,
                &y[out_pos*_channels], _olen-out_pos, &odone);
            out_pos += odone;

            if (err != NULL) throw std::runtime_error(err);
        } while (0 < odone);
        return y;
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

        T *y = nullptr;

        soxr_error_t err = NULL;
        size_t out_pos = 0;
        {
            nb::gil_scoped_release release;

            const size_t ilen = x.shape(0);

            // This is slower than returning fixed `ilen * _oi_ratio` buffers w/o copying.
            // But it ensures the lowest output delay provided by libsoxr.
            const size_t req_len = soxr_delay(_soxr) + ilen * _oi_ratio + 1;
            y = _resize_ybuf<T>(sizeof(T) * req_len * channels, false);

            // divide long input and process
            size_t odone = 0;
            for (size_t idx = 0; idx < ilen; idx += _div_len) {
                err = soxr_process(
                    _soxr,
                    &x.data()[idx*channels], std::min(_div_len, ilen-idx), NULL,
                    &y[out_pos*channels], _olen-out_pos, &odone);
                out_pos += odone;

                if (_olen <= out_pos) {
                    // for VR mode, output buffer may be full
                    y = _flush<T>(&x.data()[idx*channels], out_pos);
                }
            }

            // flush if last input
            if (last) {
                _ended = true;
                y = _flush<T>(NULL, out_pos);
            }

            // if (_olen <= out_pos) {
            //     printf("Warning: output buffer overflow %zu <= %zu\n", _olen, out_pos);
            // }
        }

        if (err) {
            throw std::runtime_error(err);
        }

        // Return a copy
        return ndarray<nb::numpy, T>(y, { out_pos, channels }).cast();
    }

    size_t num_clips() { return *soxr_num_clips(_soxr); }
    double delay() { return soxr_delay(_soxr); }
    char const * engine() { return soxr_engine(_soxr); }

    void clear() {
        soxr_error_t err = soxr_clear(_soxr);
        if (err != NULL) throw std::runtime_error(err);
        _ended = false;
    }

    void set_io_ratio(double io_ratio, size_t slew_len=0) {
        soxr_error_t err = soxr_set_io_ratio(_soxr, io_ratio, slew_len);
        if (err != NULL) throw std::runtime_error(err);
        _oi_ratio = std::max(_oi_ratio, 1 / io_ratio);
    }
};


// soxr_oneshot() becomes much slower when input is long.
// To avoid this, divide long input and process.
template <typename T>
auto csoxr_divide_proc(
        double in_rate, double out_rate,
        ndarray<const T, nb::ndim<2>, nb::c_contig, nb::device::cpu> x,
        unsigned long quality) {
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
        const size_t div_len = std::max(1000., 48000 * in_rate / out_rate);
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
    if (in_rate <= 0 || out_rate <= 0)
        throw std::invalid_argument("Sample rate should be over 0");

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
        const size_t div_len = std::max(1000., 48000 * in_rate / out_rate);
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
