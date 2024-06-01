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
#include <typeinfo>

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>

#include <soxr.h>

#include "csoxr_version.h"


using std::type_info;

namespace nb = nanobind;
using namespace nb::literals;
using nb::ndarray;


static soxr_datatype_t to_soxr_datatype(const type_info& ntype) {
    if (ntype == typeid(float))
        return SOXR_FLOAT32_I;
    else if (ntype == typeid(double))
        return SOXR_FLOAT64_I;
    else if (ntype == typeid(int32_t))
        return SOXR_INT32_I;
    else if (ntype == typeid(int16_t))
        return SOXR_INT16_I;
    else
        throw nb::type_error("Data type not support");
}


class CSoxr {
    soxr_t _soxr = nullptr;
    const double _oi_rate;

public:
    const double _in_rate;
    const double _out_rate;
    const soxr_datatype_t _ntype;
    const unsigned _channels;
    bool _ended = false;

    CSoxr(double in_rate, double out_rate, unsigned num_channels,
           soxr_datatype_t ntype, unsigned long quality) :
            _in_rate(in_rate),
            _out_rate(out_rate),
            _oi_rate(out_rate / in_rate),
            _ntype(ntype),
            _channels(num_channels) {
        soxr_error_t err = NULL;
        soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
        soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, 0);

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
        const size_t ilen = x.shape(0);

        // This is slower then allocating fixed `ilen * _oi_rate`.
        // But it insures lowest output delay provided by libsoxr.
        const size_t olen = soxr_delay(_soxr) + ilen * _oi_rate + 1;
        const unsigned channels = x.shape(1);

        if (_ended)
            throw std::runtime_error("Input after last input");

        if (channels != _channels)
            throw std::invalid_argument("Channel num mismatch");

        const soxr_datatype_t ntype = to_soxr_datatype(typeid(T));

        if (ntype != _ntype)
            throw nb::type_error("Data type mismatch");

        T *y = new T[olen * channels] { 0 };

        soxr_error_t err = NULL;
        size_t odone = 0;
        err = soxr_process(
            _soxr,
            x.data(), ilen, NULL,
            y, olen, &odone);

        if (err != NULL)
            throw std::runtime_error(err);

        // flush if last input
        size_t ldone = 0;
        if (last) {
            _ended = true;
            err = soxr_process(
                _soxr,
                NULL, 0, NULL,
                &y[odone*channels], olen-odone, &ldone);

            if (err != NULL)
                throw std::runtime_error(err);
        }
        // Delete 'y' when the 'owner' capsule expires
        nb::capsule owner(y, [](void *p) noexcept {
            delete[] (T *) p;
        });
        return ndarray<nb::numpy, T>(y, { odone+ldone, channels }, owner);
    }

    size_t num_clips() { return *soxr_num_clips(_soxr); }
    double delay() { return soxr_delay(_soxr); }
    char const * engine() { return soxr_engine(_soxr); }

    void clear() {
        soxr_error_t err = soxr_clear(_soxr);
        if (err != NULL) throw std::runtime_error(err);
        _ended = false;
    }
};


template <typename T>
auto csoxr_divide_proc(
        double in_rate, double out_rate,
        ndarray<const T, nb::ndim<2>, nb::c_contig, nb::device::cpu> x,
        unsigned long quality) {
    const unsigned channels = x.shape(1);

    const soxr_datatype_t ntype = to_soxr_datatype(typeid(T));

    // init soxr
    soxr_error_t err = NULL;
    const soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
    const soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, 0);

    soxr_t soxr = soxr_create(
        in_rate, out_rate, channels,
        &err, &io_spec, &quality_spec, NULL);

    if (err != NULL)
        throw std::runtime_error(err);

    T *y = nullptr;
    size_t out_pos = 0;
    {
        nb::gil_scoped_release release;

        // alloc
        const size_t ilen = x.shape(0);
        const size_t olen = ilen * out_rate / in_rate + 1;
        const size_t chunk_len = 48000 * in_rate / out_rate;
        y = new T[olen * channels] { 0 };

        // divide and process
        size_t odone = 0;
        for (size_t idx = 0; idx < ilen; idx += chunk_len) {
            err = soxr_process(
                soxr,
                &x.data()[idx*channels], std::min(chunk_len, ilen-idx), NULL,
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
    }

    if (err != NULL)
        throw std::runtime_error(err);

    // Delete 'y' when the 'owner' capsule expires
    nb::capsule owner(y, [](void *p) noexcept {
       delete[] (T *) p;
    });
    return ndarray<nb::numpy, T>(y, { out_pos, channels }, owner);
}


template <typename T>
auto csoxr_oneshot(
        double in_rate, double out_rate,
        ndarray<const T, nb::ndim<2>, nb::c_contig, nb::device::cpu> x,
        unsigned long quality) {
    const size_t ilen = x.shape(0);
    const size_t olen = ilen * out_rate / in_rate + 1;
    unsigned channels = x.shape(1);

    const soxr_datatype_t ntype = to_soxr_datatype(typeid(T));

    // make soxr config
    soxr_error_t err = NULL;
    const soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
    const soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, 0);

    size_t odone = 0;
    T *y = new T[olen * channels] { 0 };

    err = soxr_oneshot(
        in_rate, out_rate, channels,
        x.data(), ilen, NULL,
        y, olen, &odone,
        &io_spec, &quality_spec, NULL);

    if (err != NULL) {
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
        .def(nb::init<double, double, unsigned, soxr_datatype_t, unsigned long>())
        .def("process_float32", &CSoxr::process<float>)
        .def("process_float64", &CSoxr::process<double>)
        .def("process_int32", &CSoxr::process<int32_t>)
        .def("process_int16", &CSoxr::process<int16_t>)
        .def("num_clips", &CSoxr::num_clips)
        .def("delay", &CSoxr::delay)
        .def("engine", &CSoxr::engine)
        .def("clear", &CSoxr::clear);

    m.def("csoxr_divide_proc_float32", csoxr_divide_proc<float>);
    m.def("csoxr_divide_proc_float64", csoxr_divide_proc<double>);
    m.def("csoxr_divide_proc_int32", csoxr_divide_proc<int32_t>);
    m.def("csoxr_divide_proc_int16", csoxr_divide_proc<int16_t>);

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
